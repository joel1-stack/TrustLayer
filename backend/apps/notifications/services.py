import logging
import requests
import os
from django.conf import settings
from .models import Notification
from .sms import send_sms as _send_sms

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get('TRUSTLAYER_BASE_URL', 'https://miranda-stockish-spacially.ngrok-free.dev').rstrip('/')


class NotificationService:

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
            msg = (
                f"TrustLayer: Payment Received!\n\n"
                f"KES {deal.amount} for '{deal.description}' ({deal.deal_code}) "
                f"has been received and HELD by TrustLayer.\n\n"
                f"Deliver the item to the buyer.\n"
                f"Funds will be released to your M-Pesa only after buyer confirms delivery."
            )
            cls.send_sms(deal.merchant.phone, msg)
        # Notify buyer — payment held safely
        if deal.buyer_phone:
            confirm_link = f"{BASE_URL}/pay/{deal.session_token}/"
            msg = (
                f"TrustLayer: Payment Secured!\n\n"
                f"KES {deal.amount} for '{deal.description}' ({deal.deal_code}) "
                f"is held safely.\n\n"
                f"Your money will NOT be released until you confirm delivery.\n\n"
                f"When you receive your item, confirm here: {confirm_link}\n\n"
                f"If you did not receive what you ordered, raise a dispute at the same link.\n\n"
                f"TrustLayer \u2014 Your money is safe."
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
        msg = (
            f"TrustLayer: Your item is on the way!\n\n"
            f"Seller has marked {deal.deal_code} as DELIVERED.\n\n"
            f"Did you receive what you ordered?\n\n"
            f"Confirm delivery to release funds: {confirm_url}\n\n"
            f"Or raise a dispute if something is wrong.\n"
            f"Your KES {deal.amount} is still held safely until you decide.\n\n"
            f"TrustLayer \u2014 Safe payments. Real trust."
        )
        if deal.buyer_phone:
            cls.send_sms(deal.buyer_phone, msg)

    @classmethod
    def notify_funds_released(cls, deal):
        if deal.merchant.phone:
            msg = (
                f"TrustLayer: Funds Released!\n\n"
                f"Buyer confirmed delivery for {deal.deal_code}.\n\n"
                f"KES {deal.amount} is being released to your M-Pesa.\n\n"
                f"Thank you for using TrustLayer."
            )
            cls.send_sms(deal.merchant.phone, msg)
        if deal.buyer_phone:
            cls.send_sms(deal.buyer_phone, f"TrustLayer: Deal {deal.deal_code} complete. Thank you for using TrustLayer.")
        if deal.merchant.webhook_url:
            cls.send_webhook(deal.merchant.webhook_url, {
                'event': 'funds.released',
                'deal_code': deal.deal_code,
                'amount': str(deal.amount),
                'status': 'RELEASED',
            })

    @classmethod
    def notify_dispute_opened(cls, deal):
        if deal.merchant.phone:
            msg = (
                f"TrustLayer: Dispute Raised\n\n"
                f"Buyer raised a dispute for {deal.deal_code} (KES {deal.amount}).\n\n"
                f"Reason: {deal.dispute_reason}\n\n"
                f"KES {deal.amount} is STILL HELD. You will NOT receive funds until this is resolved.\n\n"
                f"Please respond within 48 hours or refund will be automatic.\n\n"
                f"TrustLayer \u2014 Safe payments. Real trust."
            )
            cls.send_sms(deal.merchant.phone, msg)
        if deal.buyer_phone:
            msg = (
                f"TrustLayer: Dispute Raised\n\n"
                f"Your dispute for {deal.deal_code} has been received.\n\n"
                f"KES {deal.amount} is still held safely.\n"
                f"The seller has 48 hours to respond.\n"
                f"If no response, your refund will be processed automatically.\n\n"
                f"TrustLayer \u2014 Your money is safe."
            )
            cls.send_sms(deal.buyer_phone, msg)
        if deal.merchant.webhook_url:
            cls.send_webhook(deal.merchant.webhook_url, {
                'event': 'dispute.opened',
                'deal_code': deal.deal_code,
                'reason': deal.dispute_reason,
                'status': 'DISPUTED',
            })
