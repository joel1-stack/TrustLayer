"""
Payment Views — M-Pesa STK Push + Daraja Callback + B2C Callback
"""
import json
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from apps.jwtsessions.services import JWTSessionService
from apps.merchants.models import Merchant
from apps.escrow.services import EscrowService
from apps.escrow.models import EscrowDeal
from .adapters.mpesa import mpesa
from .models import PaymentTransaction
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def initiate_payment(request):
    """POST /api/v1/pay/initiate/"""
    try:
        data  = json.loads(request.body)
        token = data.get('session_token', '').strip()
        phone = data.get('phone', '').strip()

        if not token or not phone:
            return JsonResponse({'error': 'session_token and phone required'}, status=400)

        # Resolve short_code to JWT if needed
        resolved = JWTSessionService.resolve_short_code(token)
        if resolved:
            token = resolved

        try:
            result = JWTSessionService.validate_token(token)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        payload  = result['payload']
        session  = result['session']
        merchant = result['merchant']

        # Normalise phone
        phone = phone.replace(' ', '').lstrip('+')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone

        # Create EscrowDeal in PENDING state before firing STK push
        deal = EscrowService.create_deal(
            merchant=merchant,
            amount=payload['amount'],
            description=payload.get('description', ''),
            buyer_phone=phone,
            buyer_email=payload.get('customer_email', ''),
            session_token=token,
        )

        # Fire STK Push
        stk = mpesa.stk_push(
            phone_number=phone,
            amount=int(float(payload['amount'])),
            account_reference=deal.deal_code,
            transaction_desc=(payload.get('description', 'TrustLayer Payment'))[:13],
        )

        if stk.get('success'):
            tx = PaymentTransaction.objects.create(
                merchant=merchant,
                provider='mpesa',
                provider_tx_id=stk['checkout_request_id'],
                amount=payload['amount'],
                phone_number=phone,
                description=payload.get('description', ''),
                status='initiated',
                checkout_request_id=stk['checkout_request_id'],
                merchant_request_id=stk.get('merchant_request_id', ''),
                deal_code=deal.deal_code,
            )
            # Mark session used only after STK push succeeds
            session.mark_used()
            return JsonResponse({
                'success':             True,
                'message':             'STK Push sent. Check your phone.',
                'deal_code':           deal.deal_code,
                'checkout_request_id': stk['checkout_request_id'],
            })

        # STK push failed — delete the pending deal so it doesn't pollute DB
        deal.delete()
        return JsonResponse({'success': False, 'error': stk.get('error', 'STK Push failed')}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """POST /api/v1/pay/callbacks/mpesa/ — Daraja callback"""
    try:
        data   = json.loads(request.body)
        result = mpesa.process_callback(data)
        cid    = result.get('checkout_request_id')

        if cid:
            tx = PaymentTransaction.objects.filter(checkout_request_id=cid).first()
            if tx:
                tx.callback_received = True
                tx.callback_payload  = data
                tx.callback_at       = timezone.now()

                if result['success']:
                    tx.status        = 'success'
                    tx.mpesa_receipt = result.get('mpesa_receipt', '')
                    tx.completed_at  = timezone.now()
                    tx.save()

                    # Wire callback → EscrowDeal: PENDING → HELD
                    if tx.deal_code:
                        try:
                            deal = EscrowService.confirm_payment(
                                deal_code=tx.deal_code,
                                mpesa_receipt=result.get('mpesa_receipt', ''),
                                payment_tx=tx,
                            )
                            from apps.notifications.services import NotificationService
                            NotificationService.notify_payment_received(deal)
                        except Exception:
                            pass  # Deal may already be HELD (duplicate callback)
                else:
                    tx.status      = 'failed'
                    tx.result_code = result.get('result_code')
                    tx.result_desc = result.get('result_description', '')
                    tx.save()

    except Exception:
        pass  # Always return 200 to Daraja

    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@csrf_exempt
@require_http_methods(["POST"])
def mpesa_b2c_result(request):
    """
    POST /api/v1/pay/callbacks/b2c/result/ — Safaricom POSTs here after B2C transfer.
    Handles success, insufficient funds, recipient not found, etc.
    """
    try:
        data   = json.loads(request.body)
        result = mpesa.process_b2c_result(data)
        logger.info(f"B2C result received: conv={result.get('conversation_id')} code={result.get('result_code')}")

        conversation_id = result.get('conversation_id')
        if not conversation_id:
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        deal = EscrowDeal.objects.filter(b2c_conversation_id=conversation_id).first()
        if not deal:
            logger.warning(f"B2C result for unknown conversation: {conversation_id}")
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        if result['success']:
            deal.ledger_status    = 'RELEASED'
            deal.b2c_transaction_id = result.get('transaction_id', '')
            deal.b2c_completed_at = timezone.now()
            deal.save()

            from apps.notifications.services import NotificationService
            NotificationService.notify_funds_released(deal)

            logger.info(f"B2C completed: {deal.deal_code}, TX: {result.get('transaction_id')}")
        else:
            deal.ledger_status    = 'STUCK'
            deal.b2c_failure_reason = result.get('result_desc', 'B2C transfer failed')
            deal.save()

            logger.error(f"B2C FAILED: {deal.deal_code}, Reason: {deal.b2c_failure_reason}")

    except Exception:
        pass

    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@csrf_exempt
@require_http_methods(["POST"])
def mpesa_b2c_timeout(request):
    """
    POST /api/v1/pay/callbacks/b2c/timeout/ — Safaricom timeout callback.
    B2C request timed out — funds are stuck in the paybill.
    """
    try:
        data = json.loads(request.body)
        logger.warning(f"B2C timeout received: {json.dumps(data, indent=2)[:500]}")

        result = data.get('Result', {})
        conversation_id = result.get('ConversationID')
        if conversation_id:
            deal = EscrowDeal.objects.filter(b2c_conversation_id=conversation_id).first()
            if deal:
                deal.ledger_status    = 'STUCK'
                deal.b2c_failure_reason = 'B2C request timed out — manual intervention needed'
                deal.save()
                logger.critical(f"B2C TIMEOUT for {deal.deal_code}: funds stuck in paybill")
    except Exception:
        pass

    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@csrf_exempt
@require_http_methods(["POST"])
def direct_stk_push(request):
    """POST /api/v1/pay/direct-stk/ — Merchant fires STK Push directly (no checkout link)"""
    try:
        from apps.merchants.permissions import APISecretAuthentication
        auth   = APISecretAuthentication()
        result = auth.authenticate(request)
        if not result:
            return JsonResponse({'error': 'Invalid API secret'}, status=401)
        merchant = result[0]

        data        = json.loads(request.body)
        amount      = data.get('amount')
        buyer_phone = data.get('buyer_phone', '').strip()
        description = data.get('description', '').strip()

        if not all([amount, buyer_phone, description]):
            return JsonResponse({'error': 'amount, buyer_phone, description required'}, status=400)

        phone = buyer_phone.replace(' ', '').lstrip('+')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone

        deal = EscrowService.create_deal(
            merchant=merchant,
            amount=amount,
            description=description,
            buyer_phone=phone,
            buyer_email='',
            session_token='',
        )

        stk = mpesa.stk_push(
            phone_number=phone,
            amount=int(float(amount)),
            account_reference=deal.deal_code,
            transaction_desc=description[:13],
        )

        if stk.get('success'):
            PaymentTransaction.objects.create(
                merchant=merchant,
                provider='mpesa',
                provider_tx_id=stk['checkout_request_id'],
                amount=amount,
                phone_number=phone,
                description=description,
                status='initiated',
                checkout_request_id=stk['checkout_request_id'],
                merchant_request_id=stk.get('merchant_request_id', ''),
                deal_code=deal.deal_code,
            )
            return JsonResponse({
                'success':             True,
                'message':             f'STK Push sent to {phone}',
                'deal_code':           deal.deal_code,
                'checkout_request_id': stk['checkout_request_id'],
            })

        deal.delete()
        return JsonResponse({'success': False, 'error': stk.get('error', 'STK Push failed')}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
