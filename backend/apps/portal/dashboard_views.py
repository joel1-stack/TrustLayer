"""
Dashboard Views — Real business stats + proxy endpoints for the portal.
"""
import json
import logging
from decimal import Decimal
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from apps.escrow.models import EscrowDeal
from apps.escrow.services import EscrowService
from apps.ledger.models import Account
from apps.ledger import services as ledger_services
from apps.merchants.models import Organization, Business

logger = logging.getLogger(__name__)


def _get_merchant(request):
    from apps.merchants.permissions import APIKeyAuthentication, APISecretAuthentication
    result = APIKeyAuthentication().authenticate(request)
    if not result:
        result = APISecretAuthentication().authenticate(request)
    if not result:
        mid = request.session.get('merchant_id')
        if mid:
            from apps.merchants.models import Merchant
            try:
                result = (Merchant.objects.get(id=mid, is_active=True), None)
            except Merchant.DoesNotExist:
                result = None
    return result[0] if result else None


@require_http_methods(["GET"])
def business_stats(request):
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    deals = EscrowDeal.objects.filter(merchant=merchant)

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_revenue = sum(
        d.amount for d in deals
        if d.created_at and d.created_at >= today_start and d.status in ('HELD', 'DELIVERED', 'RELEASED')
    )

    pending = sum(d.amount for d in deals if d.status in ('PENDING', 'PAYMENT_INITIATED'))
    held = sum(d.amount for d in deals if d.status in ('HELD', 'DELIVERED'))
    settled = sum(d.amount for d in deals if d.status == 'RELEASED')
    disputed = sum(d.amount for d in deals if d.status == 'DISPUTED')

    total_deals = deals.count()
    total_fees = sum(d.fee_amount or 0 for d in deals if d.status == 'RELEASED')

    wallet = Account.objects.filter(name=f'Wallet_{merchant.phone}').first()
    wallet_balance = float(wallet.balance) if wallet else 0

    return JsonResponse({
        'success': True,
        'data': {
            'today_revenue': float(today_revenue),
            'pending_settlement': float(pending + held),
            'already_settled': float(settled),
            'platform_fees': float(total_fees),
            'wallet_balance': wallet_balance,
            'total_deals': total_deals,
            'disputed_amount': float(disputed),
            'currency': 'KES',
        }
    })


@csrf_exempt
@require_http_methods(["GET"])
def portal_deals(request):
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Auth required'}, status=401)
    deals = EscrowDeal.objects.filter(merchant=merchant).order_by('-created_at')[:30]
    return JsonResponse({
        'deals': [{
            'deal_code': d.deal_code,
            'amount': float(d.amount),
            'status': d.status,
            'description': d.description,
            'created_at': d.created_at.isoformat() if d.created_at else None,
            'fee_amount': float(d.fee_amount) if d.fee_amount else 0,
        } for d in deals]
    })


@csrf_exempt
@require_http_methods(["POST"])
def portal_collect(request):
    """
    Create a deal + initiate STK push.
    Session-authenticated (or API key).
    """
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Auth required'}, status=401)

    from apps.payments.services import PaymentService

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    phone = data.get('phone', '').replace(' ', '').lstrip('+')
    amount = data.get('amount', 0)
    desc = data.get('description', 'POS Payment')

    if not phone or not amount:
        return JsonResponse({'error': 'Phone and amount required'}, status=400)

    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif not phone.startswith('254'):
        phone = '254' + phone

    try:
        deal = EscrowService.create_deal(
            merchant=merchant,
            amount=float(amount),
            description=desc,
            buyer_phone=phone,
        )
        result = PaymentService.initiate(deal, phone)
        return JsonResponse({
            'status': 'ok',
            'deal_code': deal.deal_code,
            'checkout_request_id': result.get('checkout_request_id', ''),
            'message': 'STK Push sent',
        })
    except Exception as e:
        logger.exception("portal_collect failed")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cashier_pin_login(request):
    """POST /api/proxy/cashier-login/ — cashier logs in with business PIN."""
    from apps.merchants.models import Business
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    pin = data.get('pin', '').strip()
    if not pin:
        return JsonResponse({'error': 'PIN required'}, status=400)

    biz = Business.objects.filter(cashier_pin=pin).first()
    if not biz:
        return JsonResponse({'error': 'Invalid PIN'}, status=401)

    from datetime import timedelta
    from django.utils import timezone
    from apps.merchants.models import CashierSession
    session = CashierSession.objects.create(
        business=biz,
        pin_entered=pin,
        expires_at=timezone.now() + timedelta(hours=12),
    )
    return JsonResponse({
        'status': 'ok',
        'session_id': str(session.id),
        'business': {
            'id': str(biz.id),
            'name': biz.name,
            'organization': biz.organization.name,
        },
    })


@require_http_methods(["GET"])
def portal_org_businesses(request):
    """GET /api/proxy/businesses/ — list businesses for the merchant's org."""
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Auth required'}, status=401)

    orgs = Organization.objects.filter(owner=merchant)
    data = []
    for org in orgs:
        for biz in org.businesses.all():
            data.append({
                'id': str(biz.id),
                'name': biz.name,
                'phone': biz.phone,
                'is_verified': biz.is_verified,
                'kra_pin': biz.kra_pin or '',
                'bank_name': biz.bank_name or '',
                'bank_account': biz.bank_account or '',
                'settlement_preference': biz.settlement_preference,
                'cashier_pin': biz.cashier_pin or '',
                'organization': org.name,
            })
    return JsonResponse({'businesses': data})


@csrf_exempt
@require_http_methods(["POST"])
def portal_update_business(request):
    """POST /api/proxy/businesses/update/ — update business settings."""
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Auth required'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    biz_id = data.get('id', '')
    if not biz_id:
        return JsonResponse({'error': 'Business ID required'}, status=400)

    biz = Business.objects.filter(id=biz_id, organization__owner=merchant).first()
    if not biz:
        return JsonResponse({'error': 'Business not found'}, status=404)

    for field in ['name', 'phone', 'kra_pin', 'bank_name', 'bank_account',
                  'bank_account_name', 'settlement_preference', 'cashier_pin',
                  'business_reg_number']:
        if field in data:
            setattr(biz, field, data[field])
    biz.save()

    # Also update merchant-level payout settings
    if 'payout_method' in data:
        merchant.payout_method = data['payout_method']
    if 'payout_account' in data:
        merchant.payout_account = data['payout_account']
    merchant.save()

    return JsonResponse({'status': 'ok', 'message': 'Business updated'})


@csrf_exempt
@require_http_methods(["POST"])
def portal_create_session(request):
    """
    Create a JWT payment session (checkout link) for QR code generation.
    Session-authenticated.
    """
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Auth required'}, status=401)

    from apps.jwtsessions.services import JWTSessionService

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    phone = data.get('phone', '').replace(' ', '').lstrip('+')
    amount = data.get('amount', 0)
    description = data.get('description', 'Payment')

    if not phone or not amount:
        return JsonResponse({'error': 'Phone and amount required'}, status=400)

    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif not phone.startswith('254'):
        phone = '254' + phone

    try:
        result = JWTSessionService.create_session(
            merchant=merchant,
            amount=float(amount),
            description=description,
            customer_phone=phone,
        )
        return JsonResponse({
            'status': 'ok',
            'short_code': result['short_code'],
            'checkout_url': result['checkout_url'],
            'expires_in_seconds': result['expires_in_seconds'],
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.exception("portal_create_session failed")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def portal_withdraw(request):
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Auth required'}, status=401)

    from apps.settlements.services import queue_payout

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    phone = data.get('phone', '').replace(' ', '').lstrip('+')
    amount = data.get('amount', 0)

    if not phone or not amount:
        return JsonResponse({'error': 'Phone and amount required'}, status=400)

    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif not phone.startswith('254'):
        phone = '254' + phone

    try:
        payout = queue_payout(
            merchant_phone=merchant.phone,
            amount=Decimal(str(amount)),
            method='intasend',
            destination=phone,
        )
        return JsonResponse({
            'status': 'ok',
            'payout_id': str(payout.id) if payout else '',
            'message': f'Withdrawal of KES {amount} queued to {phone}',
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.exception("portal_withdraw failed")
        return JsonResponse({'error': str(e)}, status=500)
