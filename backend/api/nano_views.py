import json, logging, base64, os, requests
from datetime import datetime
from decimal import Decimal
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import Escrow, WebhookLog

logger = logging.getLogger(__name__)


# ── Phone normaliser ──────────────────────────────────────────────────────────
def _fmt_phone(phone):
    phone = str(phone).strip().lstrip('+')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif not phone.startswith('254'):
        phone = '254' + phone
    return phone


# ── SMS notification (Africa's Talking or any SMS gateway) ───────────────────
def _sms(phone, message):
    """
    Fire-and-forget SMS. Set SMS_API_URL + SMS_API_KEY in .env.
    Payload matches Africa's Talking bulk SMS format.
    Swap the requests.post body for your gateway if different.
    """
    url = os.environ.get('SMS_API_URL', '')
    key = os.environ.get('SMS_API_KEY', '')
    sender = os.environ.get('SMS_SENDER_ID', 'TrustLayer')
    if not url or not key:
        logger.warning(f'SMS not configured — would send to {phone}: {message}')
        return
    try:
        requests.post(
            url,
            json={'to': phone, 'message': message, 'from': sender},
            headers={'apiKey': key, 'Content-Type': 'application/json'},
            timeout=8,
        )
    except Exception as ex:
        logger.error(f'SMS failed to {phone}: {ex}')


def _notify(escrow, event):
    """Send the right SMS to both parties based on the event."""
    code = escrow.deal_code
    amt  = f'KES {escrow.amount:,.0f}'
    desc = escrow.description or 'Escrow deal'

    messages = {
        'created': (
            f'TrustLayer: Deal {code} created. {amt} — {desc}. Awaiting payment.',
            f'TrustLayer: You have a pending deal {code} for {amt} — {desc}. Buyer will pay shortly.',
        ),
        'held': (
            f'TrustLayer: Your payment of {amt} for deal {code} is held in escrow. Awaiting delivery.',
            f'TrustLayer: Buyer has paid {amt} for deal {code}. Deliver to release funds.',
        ),
        'done': (
            f'TrustLayer: Deal {code} complete. Funds of {amt} released to receiver.',
            f'TrustLayer: Deal {code} complete. {amt} has been sent to you.',
        ),
        'refunded': (
            f'TrustLayer Admin: Deal {code} refunded. {amt} returns to you within 24 hrs.',
            f'TrustLayer Admin: Deal {code} cancelled. Funds returned to buyer.',
        ),
    }

    sender_msg, receiver_msg = messages.get(event, ('', ''))
    if escrow.sender_phone and sender_msg:
        _sms(escrow.sender_phone, sender_msg)
    if escrow.receiver_phone and receiver_msg:
        _sms(escrow.receiver_phone, receiver_msg)


# ── Daraja STK Push ───────────────────────────────────────────────────────────
def _get_token():
    key    = os.environ.get('MPESA_CONSUMER_KEY', '')
    secret = os.environ.get('MPESA_CONSUMER_SECRET', '')
    env    = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')
    base   = 'https://sandbox.safaricom.co.ke' if env == 'sandbox' else 'https://api.safaricom.co.ke'
    creds  = base64.b64encode(f'{key}:{secret}'.encode()).decode()
    r = requests.get(
        f'{base}/oauth/v1/generate?grant_type=client_credentials',
        headers={'Authorization': f'Basic {creds}'},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()['access_token'], base


def _stk(phone, amount, deal_code):
    token, base = _get_token()
    sc  = os.environ.get('MPESA_SHORTCODE', '174379')
    pk  = os.environ.get('MPESA_PASSKEY', '')
    cb  = os.environ.get('MPESA_CALLBACK_URL', '')
    phone = _fmt_phone(phone)
    ts  = datetime.now().strftime('%Y%m%d%H%M%S')
    pwd = base64.b64encode(f'{sc}{pk}{ts}'.encode()).decode()
    r = requests.post(
        f'{base}/mpesa/stkpush/v1/processrequest',
        json={
            'BusinessShortCode': sc, 'Password': pwd, 'Timestamp': ts,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount), 'PartyA': phone, 'PartyB': sc,
            'PhoneNumber': phone, 'CallBackURL': cb,
            'AccountReference': deal_code[:12],
            'TransactionDesc': f'Pay {deal_code}'[:13],
        },
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        timeout=15,
    )
    return r.json()


# ── Serialiser ────────────────────────────────────────────────────────────────
def _d(e):
    return {
        'deal_code':       e.deal_code,
        'sender':          e.sender.username,
        'sender_phone':    e.sender_phone,
        'receiver':        e.receiver.username if e.receiver else None,
        'receiver_phone':  e.receiver_phone,
        'amount':          str(e.amount),
        'fee':             str(e.fee),
        'fee_label':       f'KES {e.fee} (1.5%)',
        'total_payable':   str(e.total_payable),
        'state':           e.state,
        'mpesa_checkout_id': e.mpesa_checkout_id,
        'mpesa_receipt':   e.mpesa_receipt,
        'description':     e.description,
        'created_at':      e.created_at.isoformat(),
        'updated_at':      e.updated_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nano_create_deal(request):
    amt = request.data.get('amount')
    if not amt:
        return Response({'error': 'amount required'}, status=400)
    try:
        amt = Decimal(str(amt))
        assert amt > 0
    except Exception:
        return Response({'error': 'amount must be positive'}, status=400)

    sender_phone   = request.data.get('sender_phone', '').strip()
    receiver_phone = request.data.get('receiver_phone', '').strip()

    e = Escrow.objects.create(
        sender=request.user,
        amount=amt,
        description=request.data.get('description', ''),
        sender_phone=_fmt_phone(sender_phone) if sender_phone else None,
        receiver_phone=_fmt_phone(receiver_phone) if receiver_phone else None,
    )
    _notify(e, 'created')
    return Response(_d(e), status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nano_pay(request):
    code  = request.data.get('deal_code', '').strip().upper()
    phone = request.data.get('phone', '').strip()
    if not code or not phone:
        return Response({'error': 'deal_code and phone required'}, status=400)
    try:
        e = Escrow.objects.get(deal_code=code)
    except Escrow.DoesNotExist:
        return Response({'error': 'Deal not found'}, status=404)
    if e.state != Escrow.STATE_PENDING:
        return Response({'error': f'Deal is {e.state}'}, status=400)
    try:
        resp = _stk(phone, e.total_payable, code)
        if resp.get('ResponseCode') == '0':
            e.mpesa_checkout_id = resp.get('CheckoutRequestID')
            if not e.sender_phone:
                e.sender_phone = _fmt_phone(phone)
            e.save(update_fields=['mpesa_checkout_id', 'sender_phone', 'updated_at'])
            return Response({'success': True, 'message': 'STK Push sent', 'deal_code': code, 'amount_charged': str(e.total_payable)})
        return Response({'success': False, 'message': resp.get('ResponseDescription', 'Failed')}, status=400)
    except Exception as ex:
        return Response({'error': str(ex)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nano_deal_status(request, deal_code):
    try:
        e = Escrow.objects.get(deal_code=deal_code.upper())
    except Escrow.DoesNotExist:
        return Response({'error': 'Deal not found'}, status=404)
    return Response(_d(e))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nano_release(request, deal_code):
    try:
        e = Escrow.objects.get(deal_code=deal_code.upper())
    except Escrow.DoesNotExist:
        return Response({'error': 'Deal not found'}, status=404)
    if e.sender != request.user and not request.user.is_staff:
        return Response({'error': 'Only sender or admin'}, status=403)
    try:
        action = request.data.get('action')
        if action == 'refund':
            e.mark_refunded()
            _notify(e, 'refunded')
            msg = f'Deal {deal_code} refunded'
        else:
            e.mark_done()
            _notify(e, 'done')
            msg = f'Deal {deal_code} released'
        return Response({'success': True, 'message': msg, 'state': e.state})
    except ValueError as ex:
        return Response({'error': str(ex)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def nano_mpesa_callback(request):
    try:
        raw  = json.loads(request.body)
        stk  = raw.get('Body', {}).get('stkCallback', {})
        rc   = stk.get('ResultCode')
        cid  = stk.get('CheckoutRequestID', '')
        ref  = stk.get('AccountReference', '').upper()
        e    = Escrow.objects.filter(Q(deal_code=ref) | Q(mpesa_checkout_id=cid)).first()
        event = 'stk_callback_success' if rc == 0 else 'stk_callback_failure'
        WebhookLog.objects.create(escrow=e, event=event, payload=raw)
        if rc == 0:
            items   = stk.get('CallbackMetadata', {}).get('Item', [])
            receipt = next((i['Value'] for i in items if i['Name'] == 'MpesaReceiptNumber'), None)
            if e:
                try:
                    e.mark_held(mpesa_checkout_id=cid, mpesa_receipt=receipt)
                    _notify(e, 'held')
                except ValueError as ex:
                    logger.warning(f'skip: {ex}')
        return Response({'ResultCode': 0, 'ResultDesc': 'Success'})
    except Exception as ex:
        logger.error(f'callback error: {ex}')
        return Response({'ResultCode': 1, 'ResultDesc': 'Error'})
