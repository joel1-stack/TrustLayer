import base64
import requests
from datetime import datetime
from django.conf import settings
from .models import PaymentTransaction


class MPesaService:
    def __init__(self):
        env = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        self.base_url       = 'https://sandbox.safaricom.co.ke' if env == 'sandbox' else 'https://api.safaricom.co.ke'
        self.consumer_key   = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.shortcode      = getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.passkey        = getattr(settings, 'MPESA_PASSKEY', '')
        self.callback_url   = getattr(settings, 'MPESA_CALLBACK_URL', '')

    def get_access_token(self):
        creds = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        r = requests.get(f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials", headers={'Authorization': f'Basic {creds}'}, timeout=30)
        r.raise_for_status()
        return r.json()['access_token']

    def stk_push(self, phone, amount, account_reference, transaction_desc='TrustLayer Payment'):
        token     = self.get_access_token()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password  = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        phone     = self._fmt(phone)
        r = requests.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            json={
                'BusinessShortCode': self.shortcode, 'Password': password, 'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline', 'Amount': int(amount),
                'PartyA': phone, 'PartyB': self.shortcode, 'PhoneNumber': phone,
                'CallBackURL': self.callback_url,
                'AccountReference': account_reference[:12], 'TransactionDesc': transaction_desc[:13],
            },
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )
        return r.json()

    def _fmt(self, phone):
        phone = str(phone).strip().replace('+', '').replace(' ', '')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone
        return phone

    @staticmethod
    def parse_callback(data):
        stk  = data.get('Body', {}).get('stkCallback', {})
        code = stk.get('ResultCode')
        if code == 0:
            items = {i['Name']: i.get('Value') for i in stk.get('CallbackMetadata', {}).get('Item', [])}
            return {'success': True, 'receipt': items.get('MpesaReceiptNumber'), 'phone': str(items.get('PhoneNumber', '')), 'amount': items.get('Amount')}
        return {'success': False, 'error': stk.get('ResultDesc'), 'result_code': code}


class PaymentService:
    @classmethod
    def initiate(cls, deal, phone):
        mpesa  = MPesaService()
        total = deal.amount + (deal.fee_amount or 0)
        result = mpesa.stk_push(phone, total, 'TRUSTLAYER', f"TrustLayer {deal.deal_code}")
        tx = PaymentTransaction.objects.create(
            merchant=deal.merchant, provider='mpesa',
            provider_tx_id=result.get('CheckoutRequestID', ''),
            amount=total, phone_number=phone,
            description=deal.description, status='initiated',
            checkout_request_id=result.get('CheckoutRequestID', ''),
            merchant_request_id=result.get('MerchantRequestID', ''),
            deal_code=deal.deal_code,
        )
        return {'success': result.get('ResponseCode') == '0', 'transaction_id': str(tx.id), 'checkout_request_id': result.get('CheckoutRequestID')}

    @classmethod
    def handle_callback(cls, data):
        result = MPesaService.parse_callback(data)
        cid    = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
        try:
            tx = PaymentTransaction.objects.get(checkout_request_id=cid)
            if result['success']:
                tx.status        = 'success'
                tx.mpesa_receipt = result.get('receipt', '')
                tx.save()
                from apps.escrow.services import EscrowService
                try:
                    deal = __import__('apps.escrow.models', fromlist=['EscrowDeal']).EscrowDeal.objects.get(deal_code=tx.deal_code, status='PENDING')
                    EscrowService.mark_paid(deal, result.get('receipt', ''), result.get('phone', ''))
                    from apps.notifications.services import NotificationService
                    NotificationService.notify_payment_received(deal)
                except Exception:
                    pass
            else:
                tx.status      = 'failed'
                tx.result_code = result.get('result_code')
                tx.result_desc = result.get('error', '')
                tx.save()
        except PaymentTransaction.DoesNotExist:
            pass
        return result
