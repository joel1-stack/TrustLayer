"""
M-Pesa Daraja API Adapter
Handles STK Push (C2B), B2C transfers, callback processing, and status queries.
"""
import requests
import base64
from datetime import datetime
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MpesaAdapter:
    SANDBOX_BASE    = 'https://sandbox.safaricom.co.ke'
    PRODUCTION_BASE = 'https://api.safaricom.co.ke'

    def __init__(self):
        self.environment    = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        self.base_url       = self.SANDBOX_BASE if self.environment == 'sandbox' else self.PRODUCTION_BASE
        self.consumer_key   = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.shortcode      = getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.passkey        = getattr(settings, 'MPESA_PASSKEY', '')
        self.callback_url   = getattr(settings, 'MPESA_CALLBACK_URL', '')
        self.initiator_name = getattr(settings, 'MPESA_INITIATOR_NAME', 'testinitiator')
        self.initiator_password = getattr(settings, 'MPESA_INITIATOR_PASSWORD', '')
        self.b2c_result_url = getattr(settings, 'MPESA_B2C_RESULT_URL', '')
        self.b2c_timeout_url = getattr(settings, 'MPESA_B2C_TIMEOUT_URL', '')

    def _get_access_token(self) -> str:
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        credentials = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        r = requests.get(url, headers={'Authorization': f'Basic {credentials}'}, timeout=30)
        r.raise_for_status()
        return r.json()['access_token']

    def _generate_password(self) -> tuple:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password  = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        return password, timestamp

    def _fmt_phone(self, phone: str) -> str:
        phone = phone.strip().replace(' ', '').lstrip('+')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone
        return phone

    def _get_security_credential(self) -> str:
        """
        Encrypt initiator password with Safaricom's public certificate.
        In sandbox, the password itself is often used directly after base64 encoding.
        In production, you must encrypt with the official Safaricom public cert.
        """
        return base64.b64encode(self.initiator_password.encode()).decode()

    def stk_push(self, phone_number: str, amount: int,
                 account_reference: str, transaction_desc: str = 'TrustLayer Payment') -> dict:
        token             = self._get_access_token()
        password, timestamp = self._generate_password()
        phone             = self._fmt_phone(phone_number)

        payload = {
            'BusinessShortCode': self.shortcode,
            'Password':          password,
            'Timestamp':         timestamp,
            'TransactionType':   'CustomerPayBillOnline',
            'Amount':            int(amount),
            'PartyA':            phone,
            'PartyB':            self.shortcode,
            'PhoneNumber':       phone,
            'CallBackURL':       self.callback_url,
            'AccountReference':  account_reference[:12],
            'TransactionDesc':   transaction_desc[:13],
        }

        r = requests.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )

        if r.status_code == 200:
            d = r.json()
            return {
                'success':              d.get('ResponseCode') == '0',
                'checkout_request_id':  d.get('CheckoutRequestID'),
                'merchant_request_id':  d.get('MerchantRequestID'),
                'response_code':        d.get('ResponseCode'),
                'response_description': d.get('ResponseDescription'),
                'customer_message':     d.get('CustomerMessage'),
            }
        return {'success': False, 'error': r.text, 'status_code': r.status_code}

    def b2c_transfer(self, phone: str, amount: int, occasion: str, remarks: str = '') -> dict:
        """
        B2C Transfer — Pay OUT from your paybill to seller's phone.
        This is how funds are 'released' from escrow.
        Called when a deal transitions to RELEASED.
        """
        token = self._get_access_token()
        phone = self._fmt_phone(phone)

        payload = {
            'InitiatorName':      self.initiator_name,
            'SecurityCredential': self._get_security_credential(),
            'CommandID':          'BusinessPayment',
            'Amount':             int(amount),
            'PartyA':             self.shortcode,
            'PartyB':             phone,
            'Remarks':            (remarks or f'TrustLayer release {occasion}')[:100],
            'QueueTimeOutURL':    self.b2c_timeout_url,
            'ResultURL':          self.b2c_result_url,
            'Occasion':           occasion[:100],
        }

        try:
            r = requests.post(
                f"{self.base_url}/mpesa/b2c/v1/paymentrequest",
                json=payload,
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                timeout=30,
            )
            if r.status_code == 200:
                d = r.json()
                success = d.get('ResponseCode') == '0'
                logger.info(f"B2C transfer initiated: {d.get('ConversationID')} — success={success}")
                return {
                    'success':          success,
                    'conversation_id':  d.get('ConversationID'),
                    'originator_id':    d.get('OriginatorConversationID'),
                    'response_code':    d.get('ResponseCode'),
                    'response_desc':    d.get('ResponseDescription'),
                    'raw':              d,
                }
            logger.error(f"B2C HTTP error: {r.status_code} {r.text}")
            return {'success': False, 'error': f'HTTP {r.status_code}: {r.text[:200]}'}
        except requests.RequestException as e:
            logger.error(f"B2C request failed: {e}")
            return {'success': False, 'error': str(e)}

    def process_callback(self, callback_data: dict) -> dict:
        stk          = callback_data.get('Body', {}).get('stkCallback', {})
        result_code  = stk.get('ResultCode')
        receipt = phone = amount = None

        if result_code == 0:
            for item in stk.get('CallbackMetadata', {}).get('Item', []):
                name, value = item.get('Name'), item.get('Value')
                if name == 'MpesaReceiptNumber': receipt = value
                elif name == 'PhoneNumber':      phone   = str(value)
                elif name == 'Amount':           amount  = value

        return {
            'success':             result_code == 0,
            'result_code':         result_code,
            'result_description':  stk.get('ResultDesc'),
            'checkout_request_id': stk.get('CheckoutRequestID'),
            'merchant_request_id': stk.get('MerchantRequestID'),
            'mpesa_receipt':       receipt,
            'phone_number':        phone,
            'amount':              amount,
            'raw_payload':         callback_data,
        }

    def process_b2c_result(self, callback_data: dict) -> dict:
        result = callback_data.get('Result', {})
        return {
            'success':            result.get('ResultCode') == 0,
            'result_code':        result.get('ResultCode'),
            'result_desc':        result.get('ResultDesc'),
            'conversation_id':    result.get('ConversationID'),
            'originator_id':      result.get('OriginatorConversationID'),
            'transaction_id':     result.get('TransactionID'),
            'receiver_phone':     str(result.get('ReceiverPartyPublicName', '')).split(' - ')[-1] if result.get('ReceiverPartyPublicName') else '',
            'amount':             result.get('TransAmount'),
            'raw_payload':        callback_data,
        }

    def query_status(self, checkout_request_id: str) -> dict:
        token             = self._get_access_token()
        password, timestamp = self._generate_password()

        r = requests.post(
            f"{self.base_url}/mpesa/stkpushquery/v1/query",
            json={
                'BusinessShortCode': self.shortcode,
                'Password':          password,
                'Timestamp':         timestamp,
                'CheckoutRequestID': checkout_request_id,
            },
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )

        if r.status_code == 200:
            d = r.json()
            return {
                'success':             d.get('ResultCode') == 0,
                'result_code':         d.get('ResultCode'),
                'result_description':  d.get('ResultDesc'),
                'checkout_request_id': d.get('CheckoutRequestID'),
            }
        return {'success': False, 'error': r.text}


# Singleton
mpesa = MpesaAdapter()
