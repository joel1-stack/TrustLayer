"""
Escrow Views — Deal status, confirm delivery, release funds.
"""
import json
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import EscrowDeal
from .services import EscrowService
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def deals_list(request):
    """GET /api/v1/deals/ — merchant's own deals"""
    from apps.merchants.permissions import APIKeyAuthentication, APISecretAuthentication
    result = APIKeyAuthentication().authenticate(request)
    if not result:
        result = APISecretAuthentication().authenticate(request)
    if not result:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    merchant = result[0]

    deals = EscrowDeal.objects.filter(merchant=merchant).order_by('-created_at')[:50]
    return JsonResponse({
        'success': True,
        'deals': [{
            'deal_code':      d.deal_code,
            'amount':         str(d.amount),
            'status':         d.status,
            'ledger_status':  d.ledger_status,
            'buyer_phone':    d.buyer_phone,
            'description':    d.description,
            'created_at':     d.created_at.isoformat(),
        } for d in deals]
    })


@csrf_exempt
@require_http_methods(["GET"])
def deal_status(request, deal_code):
    """GET /api/v1/deals/<deal_code>/"""
    try:
        deal = EscrowDeal.objects.get(deal_code=deal_code)
        return JsonResponse({
            'success': True,
            'deal': {
                'deal_code':         deal.deal_code,
                'status':            deal.status,
                'ledger_status':     deal.ledger_status,
                'amount':            str(deal.amount),
                'amount_released':   str(deal.amount_released),
                'fee_charged':       str(deal.fee_charged),
                'description':       deal.description,
                'buyer_phone':       deal.buyer_phone,
                'buyer_confirmed':   deal.buyer_confirmed,
                'seller_confirmed':  deal.seller_confirmed,
                'mpesa_receipt':     deal.mpesa_receipt,
                'b2c_transaction_id': deal.b2c_transaction_id,
                'auto_release_at':   deal.auto_release_at.isoformat() if deal.auto_release_at else None,
                'created_at':        deal.created_at.isoformat(),
                'updated_at':        deal.updated_at.isoformat(),
            },
        })
    except EscrowDeal.DoesNotExist:
        return JsonResponse({'error': 'Deal not found'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def buyer_confirm(request, deal_code):
    """POST /api/v1/deals/<deal_code>/confirm/"""
    try:
        deal = EscrowService.buyer_confirm_delivery(deal_code)

        # If deal is now RELEASED, trigger B2C fund release
        if deal.status == 'RELEASED':
            release = EscrowService.release_funds(deal_code)
            if not release.get('success'):
                logger.error(f"Fund release failed after buyer confirm: {release.get('error')}")

        from apps.notifications.services import NotificationService
        if deal.status == 'RELEASED':
            NotificationService.notify_funds_released(deal)

        return JsonResponse({
            'success': True,
            'status': deal.status,
            'ledger_status': deal.ledger_status,
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except EscrowDeal.DoesNotExist:
        return JsonResponse({'error': 'Deal not found'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def seller_deliver(request, deal_code):
    """POST /api/v1/deals/<deal_code>/seller-deliver/ — HELD → DELIVERED"""
    try:
        from apps.merchants.permissions import APISecretAuthentication
        result = APISecretAuthentication().authenticate(request)
        if not result:
            return JsonResponse({'error': 'API secret required'}, status=401)
        merchant = result[0]

        deal = EscrowDeal.objects.get(deal_code=deal_code, merchant=merchant)
        if deal.status != 'HELD':
            return JsonResponse({'error': f'Cannot deliver from {deal.status} status'}, status=400)

        deal.status = 'DELIVERED'
        deal.save(update_fields=['status', 'updated_at'])

        try:
            from apps.notifications.services import NotificationService
            confirm_url = f"{request.scheme}://{request.get_host()}/api/v1/deals/{deal.deal_code}/confirm/"
            NotificationService.notify_seller_delivered(deal, confirm_url=confirm_url)
        except Exception:
            pass

        return JsonResponse({'success': True, 'deal_code': deal_code, 'status': 'DELIVERED'})
    except EscrowDeal.DoesNotExist:
        return JsonResponse({'error': 'Deal not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def raise_dispute(request, deal_code):
    """POST /api/v1/deals/<deal_code>/dispute/"""
    try:
        data   = json.loads(request.body) if request.body else {}
        reason = data.get('reason', 'Buyer initiated dispute')
        deal   = EscrowDeal.objects.get(deal_code=deal_code)
        if deal.status not in ('HELD', 'DELIVERED'):
            return JsonResponse({'error': f'Cannot dispute from {deal.status} status'}, status=400)
        deal.status         = 'DISPUTED'
        deal.dispute_reason = reason
        deal.disputed_at    = timezone.now()
        deal.save(update_fields=['status', 'dispute_reason', 'disputed_at', 'updated_at'])
        from apps.notifications.services import NotificationService
        NotificationService.notify_dispute_opened(deal)
        return JsonResponse({'success': True, 'status': deal.status})
    except EscrowDeal.DoesNotExist:
        return JsonResponse({'error': 'Deal not found'}, status=404)
