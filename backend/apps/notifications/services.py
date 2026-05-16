import logging
import requests
from django.conf import settings
from .models import Notification
from .sms import send_sms as _send_sms

logger = logging.getLogger(__name__)


class NotificationService:

    TEMPLATES = {
        'payment_received': 'TrustLayer: Payment of KES {amount} received for deal {deal_code}. Funds held in escrow until delivery confirmed.',
        'funds_released':   'TrustLayer: KES {amount} released for deal {deal_code}. Funds sent to your account.',
        'dispute_opened':   'TrustLayer: Dispute opened for deal {deal_code}. Admin will review within 48 hours.',
        'seller_delivered': 'TrustLayer: Seller marked deal {deal_code} as delivered. Please confirm receipt or raise a dispute at your payment link.',
    }

    @classmethod
    def send_sms(cls, phone: str, message: str) -> dict:
        """Send SMS and log to Notification table."""
        result = _send_sms(phone, message)
        status = 'SENT' if result.get('success') else 'FAILED'
        try:
            Notification.objects.create(
                recipient=phone,
                channel='SMS',
                template_name='custom',
                body=message,
                status=status,
                error_message=result.get('error', ''),
            )
        except Exception:
            pass
        return result

    @classmethod
    def send_webhook(cls, url: str, payload: dict) -> dict:
        try:
            r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
            status = 'SENT' if r.status_code < 300 else 'FAILED'
            Notification.objects.create(recipient=url, channel='WEBHOOK', template_name='webhook', body=str(payload), status=status)
            return {'success': status == 'SENT'}
        except Exception as e:
            Notification.objects.create(recipient=url, channel='WEBHOOK', template_name='webhook', body=str(payload), status='FAILED', error_message=str(e))
            return {'success': False, 'error': str(e)}

    @classmethod
    def notify_payment_received(cls, deal):
        msg = cls.TEMPLATES['payment_received'].format(deal_code=deal.deal_code, amount=deal.amount)
        # Notify merchant (seller)
        if deal.merchant.phone:
            cls.send_sms(deal.merchant.phone, msg)
        # Notify buyer
        if deal.buyer_phone:
            buyer_msg = f'TrustLayer: Your payment of KES {deal.amount} for deal {deal.deal_code} is secured in escrow. Funds release after delivery confirmation.'
            cls.send_sms(deal.buyer_phone, buyer_msg)
        # Webhook
        if deal.merchant.webhook_url:
            cls.send_webhook(deal.merchant.webhook_url, {
                'event': 'payment.received',
                'deal_code': deal.deal_code,
                'amount': str(deal.amount),
                'status': 'HELD',
            })

    @classmethod
    def notify_seller_delivered(cls, deal):
        msg = cls.TEMPLATES['seller_delivered'].format(deal_code=deal.deal_code)
        if deal.buyer_phone:
            cls.send_sms(deal.buyer_phone, msg)

    @classmethod
    def notify_funds_released(cls, deal):
        msg = cls.TEMPLATES['funds_released'].format(deal_code=deal.deal_code, amount=deal.amount)
        if deal.merchant.phone:
            cls.send_sms(deal.merchant.phone, msg)
        if deal.buyer_phone:
            buyer_msg = f'TrustLayer: Deal {deal.deal_code} complete. Thank you for using TrustLayer.'
            cls.send_sms(deal.buyer_phone, buyer_msg)
        if deal.merchant.webhook_url:
            cls.send_webhook(deal.merchant.webhook_url, {
                'event': 'funds.released',
                'deal_code': deal.deal_code,
                'amount': str(deal.amount),
                'status': 'RELEASED',
            })

    @classmethod
    def notify_dispute_opened(cls, deal):
        msg = cls.TEMPLATES['dispute_opened'].format(deal_code=deal.deal_code)
        if deal.merchant.phone:
            cls.send_sms(deal.merchant.phone, msg)
        if deal.buyer_phone:
            cls.send_sms(deal.buyer_phone, msg)
        if deal.merchant.webhook_url:
            cls.send_webhook(deal.merchant.webhook_url, {
                'event': 'dispute.opened',
                'deal_code': deal.deal_code,
                'reason': deal.dispute_reason,
                'status': 'DISPUTED',
            })
