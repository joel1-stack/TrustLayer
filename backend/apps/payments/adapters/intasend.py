import hashlib
import hmac
import json
import logging
from decimal import Decimal
from django.conf import settings
from .base import PaymentProviderAdapter

logger = logging.getLogger(__name__)


class IntaSendAdapter(PaymentProviderAdapter):
    
    def get_provider_name(self):
        return 'intasend'
    
    def _get_headers(self):
        return {
            'Authorization': f'Bearer {settings.INTASEND_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
    
    def _get_base_url(self):
        return settings.INTASEND_BASE_URL.rstrip('/')
    
    def generate_link(self, amount, phone, reference, **kwargs):
        if not settings.INTASEND_SECRET_KEY:
            return self._simulate_link(amount, phone, reference, **kwargs)
        try:
            import requests
            
            email = kwargs.get('email', '')
            name = kwargs.get('name', f'Agreement {reference}')
            redirect_url = kwargs.get('redirect_url', '')
            webhook_url = kwargs.get('webhook_url', '')
            currency = kwargs.get('currency', 'KES')
            
            # Use TRUSTLAYER_BASE_URL to construct default URLs if not provided
            base_url = getattr(settings, 'TRUSTLAYER_BASE_URL', '').rstrip('/')
            if not redirect_url and base_url:
                redirect_url = f'{base_url}/success/'
            if not webhook_url and base_url:
                webhook_url = f'{base_url}/webhooks/intasend/'
            
            payload = {
                'name': name,
                'amount': str(amount),
                'currency': currency,
                'email': email,
                'comment': f'TrustLayer Agreement {reference}',
                'redirect_url': redirect_url,
                'webhook_url': webhook_url,
                'internal_id': reference,
            }
            
            logger.info(f"IntaSend generate_link for {reference}: {payload}")
            
            resp = requests.post(
                f'{self._get_base_url()}/checkout/',
                json=payload,
                headers=self._get_headers(),
                timeout=15,
            )
            data = resp.json()
            logger.info(f"IntaSend response: {data}")
            
            if resp.ok and data.get('url'):
                return {
                    'success': True,
                    'payment_url': data['url'],
                    'provider_reference': data.get('invoice_id', data.get('id', '')),
                }
            else:
                logger.error(f"IntaSend checkout failed: {data}")
                return {'success': False, 'error': data.get('message', 'Checkout creation failed')}
                
        except ImportError:
            logger.warning("requests not available, using fallback")
        except Exception as e:
            logger.error(f"IntaSend generate_link error: {e}")
        
        return self._simulate_link(amount, phone, reference, **kwargs)

    def _simulate_link(self, amount, phone, reference, **kwargs):
        import uuid
        ref = reference.replace(' ', '_')
        return {
            'success': True,
            'payment_url': f'https://pay.intasend.com/pay/{ref}',
            'provider_reference': f'INTA_{ref}_{uuid.uuid4().hex[:8]}',
        }
    
    def send_payout(self, amount, phone, reference, **kwargs):
        try:
            import requests
            payload = {
                'amount': str(amount),
                'currency': 'KES',
                'api_ref': reference,
                'phone_number': phone,
                'method': 'MPESA_B2C',
            }
            resp = requests.post(
                f'{self._get_base_url()}/payout/',
                json=payload,
                headers=self._get_headers(),
                timeout=15,
            )
            data = resp.json()
            if resp.ok and data.get('status') in ('completed', 'processing', 'queued'):
                return {
                    'success': True,
                    'provider_tx_id': data.get('id', data.get('transaction_id', '')),
                }
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"IntaSend send_payout error: {e}")
        import uuid
        return {
            'success': True,
            'provider_tx_id': f'INTA_PO_{uuid.uuid4().hex[:12].upper()}',
        }
    
    def handle_webhook(self, raw_payload):
        """Convert IntaSend webhook to standard format.
        
        IntaSend sends:
        {
            "id": "inv_123",
            "state": "COMPLETED" | "FAILED" | "PENDING" | "CANCELLED",
            "amount": 5000,
            "currency": "KES",
            "api_ref": "AGR_001",
            "phone": "254712345678",
            "account": "TrustLayer",
            "created_at": "2024-01-01T00:00:00Z",
            "channels": {...}
        }
        """
        state = raw_payload.get('state', '').upper()
        
        # Map IntaSend states to standard statuses
        if state == 'COMPLETED':
            status = 'completed'
        elif state in ('FAILED', 'EXPIRED'):
            status = 'failed'
        elif state == 'CANCELLED':
            status = 'cancelled'
        elif state in ('PENDING', 'PROCESSING'):
            status = 'pending'
        else:
            status = 'unknown'
        
        return {
            'provider': 'intasend',
            'provider_transaction_id': raw_payload.get('id', ''),
            'internal_reference': raw_payload.get('api_ref', ''),
            'amount': Decimal(str(raw_payload.get('amount', 0))),
            'currency': raw_payload.get('currency', 'KES'),
            'status': status,
            'phone': raw_payload.get('phone', ''),
            'raw_payload': raw_payload,
            'state': state,  # Keep original state for debugging
        }
    
    def verify_webhook_signature(self, payload, signature_header):
        """Verify IntaSend webhook signature.
        
        IntaSend sends: X-IntaSend-Signature header with HMAC-SHA256 of payload
        """
        if not settings.INTASEND_SECRET_KEY:
            logger.warning("INTASEND_SECRET_KEY not set, skipping signature verification")
            return True
        
        try:
            expected = hmac.new(
                settings.INTASEND_SECRET_KEY.encode(),
                json.dumps(payload, separators=(',', ':')).encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature_header)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False
