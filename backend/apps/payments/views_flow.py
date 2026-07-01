"""
IntaSend Webhook + Full A-Z Flow Views
- intasend_callback: Called by IntaSend when STK Push completes (wires into ledger)
- trigger_collect: Send STK Push to buyer
- trigger_payout: Send B2C payout to merchant
- check_wallet: Check IntaSend wallet balance
- full_flow: One-call A-Z: collect → hold → release → payout
"""
import json
import uuid
import logging
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .adapters.intasend import intasend
from apps.ledger import services as ledger

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def intasend_callback(request):
    """
    POST /api/v1/pay/webhooks/intasend/
    IntaSend calls this when STK Push succeeds.
    Wires money into the ledger automatically.
    """
    try:
        data = json.loads(request.body)
        state = data.get('state', '')
        logger.info(f"IntaSend callback: state={state}, invoice={data.get('invoice_id')}")

        if state != 'completed':
            return JsonResponse({'status': 'ignored'})

        phone = data.get('phone_number', '')
        amount = Decimal(str(data.get('amount', 0)))
        invoice_id = data.get('invoice_id', '')
        api_ref = data.get('api_ref', '')
        name = data.get('name', phone)

        # Record payment in ledger — money hits the float
        txn = ledger.record_payment(
            reference_id=invoice_id,
            phone=phone,
            amount=amount,
            name=name,
            provider='intasend',
            provider_tx_id=invoice_id,
            description=f'IntaSend payment {api_ref}',
        )

        # If api_ref references an escrow deal, auto-hold in escrow
        if api_ref and api_ref.startswith('TL-') or api_ref.startswith('ORDER_'):
            from apps.escrow.models import EscrowDeal
            deal = EscrowDeal.objects.filter(deal_code=api_ref).first()
            if deal and deal.status == 'PENDING':
                deal.status = 'HELD'
                deal.ledger_status = 'HELD'
                deal.mpesa_receipt = invoice_id
                deal.amount_paid = amount
                deal.save()

                ledger.hold_in_escrow(
                    reference_id=invoice_id,
                    phone=phone,
                    amount=amount,
                    description=f'Escrow hold for deal {api_ref}',
                )

                from apps.notifications.services import NotificationService
                try:
                    NotificationService.notify_payment_received(deal)
                except Exception:
                    pass

        return JsonResponse({'status': 'ok', 'reference_id': invoice_id})
    except Exception as e:
        logger.error(f"IntaSend callback error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def trigger_collect(request):
    """
    POST /api/v1/pay/flow/collect/
    Send STK Push to buyer via IntaSend.
    Body: {"phone": "2547...", "amount": 1000, "api_ref": "TL-XXXXXX"}
    """
    try:
        data = json.loads(request.body)
        phone = data.get('phone', '').strip()
        amount = data.get('amount')
        api_ref = data.get('api_ref', '')

        if not phone or not amount:
            return JsonResponse({'error': 'phone and amount required'}, status=400)

        result = intasend.collect_mpesa(phone, int(float(amount)), api_ref)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def trigger_payout(request):
    """
    POST /api/v1/pay/flow/payout/
    Send B2C payout to merchant via IntaSend.
    Body: {"phone": "2547...", "amount": 950, "name": "Merchant Name"}
    """
    try:
        data = json.loads(request.body)
        phone = data.get('phone', '').strip()
        amount = data.get('amount')
        name = data.get('name', 'Merchant')

        if not phone or not amount:
            return JsonResponse({'error': 'phone and amount required'}, status=400)

        result = intasend.send_payout(phone, int(float(amount)), name)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_wallet(request):
    """
    GET /api/v1/pay/flow/wallet/
    Check IntaSend wallet balance.
    """
    try:
        balance = intasend.check_balance()
        return JsonResponse(balance)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def full_flow(request):
    """
    POST /api/v1/pay/flow/full/
    ONE ENDPOINT — Full A-Z flow:
    1. Create escrow deal
    2. Send STK Push to buyer
    3. Webhook arrives → ledger records payment → escrow holds
    4. Release escrow → payout merchant
    Body: {"buyer_phone": "2547...", "amount": 1000, "description": "Wash & Fold"}
    """
    try:
        data = json.loads(request.body)
        buyer_phone = data.get('buyer_phone', '').strip()
        amount = data.get('amount')
        description = data.get('description', 'TrustLayer payment')

        if not buyer_phone or not amount:
            return JsonResponse({'error': 'buyer_phone and amount required'}, status=400)

        # Step 1: Create escrow deal
        from apps.escrow.models import EscrowDeal
        from apps.merchants.models import Merchant

        merchant = Merchant.objects.filter(is_active=True).first()
        if not merchant:
            return JsonResponse({'error': 'No merchant configured'}, status=400)

        deal = EscrowDeal.objects.create(
            merchant=merchant,
            deal_code=f'TL-{uuid.uuid4().hex[:6].upper()}',
            amount=amount,
            fee_amount=amount * Decimal('0.05'),
            description=description,
            buyer_phone=buyer_phone,
            status='PENDING',
        )

        # Step 2: Send STK Push
        result = intasend.collect_mpesa(buyer_phone, int(float(amount)), deal.deal_code)

        return JsonResponse({
            'success': True,
            'deal_code': deal.deal_code,
            'message': 'STK Push sent. On callback, money will be held in escrow.',
            'stk_result': result,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
