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
