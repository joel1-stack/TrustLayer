"""
IntaSend Adapter — Collect M-Pesa STK Push + Send B2C Payouts.
Live wallet: https://payment.intasend.com/api/v1
"""
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class IntaSendAdapter:
    def __init__(self):
        self.base_url = settings.INTASEND_BASE_URL.rstrip('/')
        self.secret_key = settings.INTASEND_SECRET_KEY
        self.public_key = settings.INTASEND_PUBLIC_KEY
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }

    def check_balance(self) -> dict:
        resp = requests.get(f'{self.base_url}/wallets/', headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def collect_mpesa(self, phone: str, amount: int, api_ref: str) -> dict:
        payload = {
            'phone': phone,
            'amount': float(amount),
            'api_ref': api_ref,
            'callback_url': settings.INTASEND_CALLBACK_URL,
        }
        resp = requests.post(
            f'{self.base_url}/payment/mpesa-stk-push/',
            json=payload,
            headers=self.headers,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return {'success': False, 'error': resp.text, 'status_code': resp.status_code}

    def send_payout(self, phone: str, amount: int, name: str = 'Merchant', narrative: str = 'TrustLayer settlement') -> dict:
        payload = {
            'currency': 'KES',
            'transactions': [{
                'name': name,
                'account': phone,
                'amount': float(amount),
                'narrative': narrative,
            }],
        }
        resp = requests.post(
            f'{self.base_url}/payouts/',
            json=payload,
            headers=self.headers,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        return {'success': False, 'error': resp.text, 'status_code': resp.status_code}

    def verify_transaction(self, invoice_id: str) -> dict:
        resp = requests.get(
            f'{self.base_url}/payment/status/{invoice_id}/',
            headers=self.headers,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return {'success': False, 'error': resp.text}


intasend = IntaSendAdapter()
