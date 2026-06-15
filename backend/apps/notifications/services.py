import logging
import requests
from django.conf import settings
from .models import Notification
from .sms import send_sms as _send_sms

logger = logging.getLogger(__name__)


class NotificationService:

    TEMPLATES = {
        'payment_received': 'TrustLayer: KES {amount} received for "{description}" ({deal_code}). Deliver the item to get paid.',
        'payment_held_buyer': 'TrustLayer: KES {amount} held safely for "{description}" ({deal_code}). Funds released after you confirm delivery.',
        'funds_released':   'TrustLayer: Buyer confirmed delivery for {deal_code}. KES {amount} released to your M-Pesa.',
        'dispute_opened':   'TrustLayer: Dispute opened for {deal_code}. Admin will review within 48 hours.',
        'seller_delivered': 'TrustLayer: Seller marked {deal_code} as delivered. Confirm delivery to release KES {amount}: {confirm_url}',
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
        # Notify merchant (seller) — payment received, deliver item
        if deal.merchant.phone:
            msg = cls.TEMPLATES['payment_received'].format(
                deal_code=deal.deal_code, amount=deal.amount, description=deal.description
            )
            cls.send_sms(deal.merchant.phone, msg)
        # Notify buyer — payment held safely
        if deal.buyer_phone:
            msg = cls.TEMPLATES['payment_held_buyer'].format(
                deal_code=deal.deal_code, amount=deal.amount, description=deal.description
            )
            cls.send_sms(deal.buyer_phone, msg)
        # Webhook
        if deal.merchant.webhook_url:
            cls.send_webhook(deal.merchant.webhook_url, {
                'event': 'payment.received',
                'deal_code': deal.deal_code,
                'amount': str(deal.amount),
                'status': 'HELD',
            })

    @classmethod
    def notify_seller_delivered(cls, deal, confirm_url=''):
        msg = cls.TEMPLATES['seller_delivered'].format(
            deal_code=deal.deal_code, amount=deal.amount, confirm_url=confirm_url
        )
        if deal.buyer_phone:
            cls.send_sms(deal.buyer_phone, msg)

    @classmethod
    def notify_funds_released(cls, deal):
        if deal.merchant.phone:
            msg = cls.TEMPLATES['funds_released'].format(deal_code=deal.deal_code, amount=deal.amount)
            cls.send_sms(deal.merchant.phone, msg)
        if deal.buyer_phone:
            cls.send_sms(deal.buyer_phone, f'TrustLayer: Deal {deal.deal_code} complete. Thank you for using TrustLayer.')
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
