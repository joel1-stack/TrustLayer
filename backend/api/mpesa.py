import requests
import base64
from datetime import datetime
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MpesaClient:
    """M-PESA Daraja API Client for STK Push"""
    
    def __init__(self):
        self.environment = settings.MPESA_ENVIRONMENT
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        
        if self.environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'
    
    def get_access_token(self):
        """Get OAuth access token from M-PESA"""
        try:
            url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            credentials = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()
            
            headers = {'Authorization': f'Basic {credentials}'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json().get('access_token')
        except Exception as e:
            logger.error(f"Error getting M-PESA access token: {str(e)}")
            return None
    
    def generate_password(self, timestamp):
        """Generate M-PESA password"""
        data = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data.encode()).decode()
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK Push to customer's phone"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return {'error': 'Failed to get access token'}
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self.generate_password(timestamp)
            
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": self.shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": settings.MPESA_CALLBACK_URL,
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc
            }
            
            logger.info(f"Sending STK Push to {phone_number} for KES {amount}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error in STK Push: {str(e)}")
            return {'error': str(e)}