import base64
import json
import logging
from datetime import datetime
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class MpesaDaraja:
    """Safaricom M-Pesa Daraja API client.

    Supports:
      - STK Push (Lipa Na M-Pesa Online) — collect payment from customer
      - B2C (Business to Customer) — send payout to seller/platform
      - Transaction status query
    """

    SANDBOX_BASE = 'https://sandbox.safaricom.co.ke'
    LIVE_BASE = 'https://api.safaricom.co.ke'

    def __init__(self):
        self.env = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        self.base_url = self.LIVE_BASE if self.env == 'live' else self.SANDBOX_BASE
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.shortcode = getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        self.initiator_name = getattr(settings, 'MPESA_INITIATOR_NAME', 'testinitiator')
        self.initiator_password = getattr(settings, 'MPESA_INITIATOR_PASSWORD', '')
        self.b2c_result_url = getattr(settings, 'MPESA_B2C_RESULT_URL', '')
        self.b2c_timeout_url = getattr(settings, 'MPESA_B2C_TIMEOUT_URL', '')
        self._token = None
        self._token_expiry = 0

    def _get_token(self):
        if self._token and datetime.now().timestamp() < self._token_expiry:
            return self._token
        if not self.consumer_key or not self.consumer_secret:
            raise ValueError('MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET must be configured')
        auth = base64.b64encode(f'{self.consumer_key}:{self.consumer_secret}'.encode()).decode()
        resp = requests.get(
            f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials',
            headers={'Authorization': f'Basic {auth}'},
            timeout=15,
        )
        data = resp.json()
        self._token = data.get('access_token', '')
        expires_in = data.get('expires_in', 3599)
        self._token_expiry = datetime.now().timestamp() + expires_in - 60
        return self._token

    def _headers(self):
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json',
        }

    def stk_push(self, phone_number, amount, account_reference='TL', transaction_desc='TrustLayer Payment'):
        """Trigger STK Push to customer's phone."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_encode = f'{self.shortcode}{self.passkey}{timestamp}'
        password = base64.b64encode(data_to_encode.encode()).decode()
        phone = self._format_phone(phone_number)
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(round(float(amount))),
            'PartyA': phone,
            'PartyB': self.shortcode,
            'PhoneNumber': phone,
            'CallBackURL': self.callback_url or 'https://sandbox.safaricom.co.ke/mpesa/',
            'AccountReference': account_reference[:12],
            'TransactionDesc': transaction_desc[:13],
        }
        resp = requests.post(
            f'{self.base_url}/mpesa/stkpush/v1/processrequest',
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        return resp.json() if resp.ok else {'success': False, 'error': resp.text}

    def b2c_payment(self, phone_number, amount, remarks='TrustLayer Payout', occasion=''):
        """Send money from business to customer (B2C payout)."""
        if not self.initiator_password:
            raise ValueError('MPESA_INITIATOR_PASSWORD must be configured for B2C')
        security_credential = base64.b64encode(self.initiator_password.encode()).decode()
        payload = {
            'InitiatorName': self.initiator_name,
            'SecurityCredential': security_credential,
            'CommandID': 'BusinessPayment',
            'Amount': int(round(float(amount))),
            'PartyA': self.shortcode,
            'PartyB': self._format_phone(phone_number),
            'Remarks': remarks[:100],
            'QueueTimeOutURL': self.b2c_timeout_url or f'{self.base_url}/mpesa/b2c/timeout',
            'ResultURL': self.b2c_result_url or f'{self.base_url}/mpesa/b2c/result',
            'Occasion': occasion[:100] if occasion else '',
        }
        resp = requests.post(
            f'{self.base_url}/mpesa/b2c/v1/paymentrequest',
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        return resp.json() if resp.ok else {'success': False, 'error': resp.text}

    def query_status(self, checkout_request_id):
        """Check STK Push transaction status."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f'{self.shortcode}{self.passkey}{timestamp}'.encode()).decode()
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id,
        }
        resp = requests.post(
            f'{self.base_url}/mpesa/stkpushquery/v1/query',
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        return resp.json() if resp.ok else {'success': False, 'error': resp.text}

    @staticmethod
    def _format_phone(phone):
        cleaned = ''.join(c for c in phone if c.isdigit())
        if cleaned.startswith('0'):
            cleaned = '254' + cleaned[1:]
        elif cleaned.startswith('+'):
            cleaned = cleaned[1:]
        elif not cleaned.startswith('254'):
            cleaned = '254' + cleaned
        return cleaned

    @staticmethod
    def stk_callback_to_standard(raw_body):
        """Parse M-Pesa STK Push callback into standard format."""
        body = raw_body.get('Body', {})
        stk = body.get('stkCallback', {})
        checkout_id = stk.get('CheckoutRequestID', '')
        result_code = stk.get('ResultCode', 1)
        result_desc = stk.get('ResultDesc', '')
        metadata = stk.get('CallbackMetadata', {}).get('Item', [])
        mpesa_receipt = ''
        amount = 0
        phone = ''
        for item in metadata:
            name = item.get('Name', '')
            if name == 'MpesaReceiptNumber':
                mpesa_receipt = item.get('Value', '')
            elif name == 'Amount':
                amount = item.get('Value', 0)
            elif name == 'PhoneNumber':
                phone = str(item.get('Value', ''))
        return {
            'provider': 'mpesa',
            'provider_transaction_id': mpesa_receipt,
            'internal_reference': checkout_id,
            'amount': amount,
            'currency': 'KES',
            'status': 'completed' if result_code == 0 else 'failed',
            'phone': phone,
            'result_code': result_code,
            'result_desc': result_desc,
            'raw_payload': raw_body,
        }
