import requests
from django.conf import settings
from .models import Notification


class NotificationService:

    TEMPLATES = {
        'deal_created':     {'sms': 'TrustLayer: Deal {deal_code} created. KES {amount}. Pay: {payment_url}'},
        'payment_received': {'sms': 'TrustLayer: Payment received for deal {deal_code}. KES {amount} held in escrow.'},
        'funds_released':   {'sms': 'TrustLayer: Funds released for deal {deal_code}. KES {amount} sent to your account.'},
        'dispute_opened':   {'sms': 'TrustLayer: Dispute opened for deal {deal_code}. Submit evidence within 24 hours.'},
    }

    @classmethod
    def send_sms(cls, phone, message):
        url = getattr(settings, 'SMS_API_URL', '')
        key = getattr(settings, 'SMS_API_KEY', '')
        if not url or not key:
            import logging
            logging.getLogger(__name__).warning(f'SMS not configured — would send to {phone}: {message}')
            Notification.objects.create(recipient=phone, channel='SMS', template_name='custom', body=message, status='FAILED', error_message='SMS not configured')
            return {'success': False}
        try:
            requests.post(url, json={'to': phone, 'message': message}, headers={'apiKey': key}, timeout=8)
            Notification.objects.create(recipient=phone, channel='SMS', template_name='custom', body=message, status='SENT')
            return {'success': True}
        except Exception as e:
            Notification.objects.create(recipient=phone, channel='SMS', template_name='custom', body=message, status='FAILED', error_message=str(e))
            return {'success': False, 'error': str(e)}

    @classmethod
    def send_webhook(cls, url, payload):
        try:
            r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
            status = 'SENT' if r.status_code == 200 else 'FAILED'
            Notification.objects.create(recipient=url, channel='WEBHOOK', template_name='webhook', body=str(payload), status=status)
            return {'success': r.status_code == 200}
        except Exception as e:
            Notification.objects.create(recipient=url, channel='WEBHOOK', template_name='webhook', body=str(payload), status='FAILED', error_message=str(e))
            return {'success': False, 'error': str(e)}

    @classmethod
    def notify_payment_received(cls, deal):
        ctx = {'deal_code': deal.deal_code, 'amount': deal.amount}
        msg = cls.TEMPLATES['payment_received']['sms'].format(**ctx)
        if deal.merchant.phone:
            cls.send_sms(deal.merchant.phone, msg)
        if deal.webhook_url:
            cls.send_webhook(deal.webhook_url, {'event': 'payment.received', 'deal_code': deal.deal_code, 'amount': str(deal.amount), 'status': 'HELD'})

    @classmethod
    def notify_funds_released(cls, deal):
        ctx = {'deal_code': deal.deal_code, 'amount': deal.amount}
        msg = cls.TEMPLATES['funds_released']['sms'].format(**ctx)
        if deal.merchant.phone:
            cls.send_sms(deal.merchant.phone, msg)
        if deal.webhook_url:
            cls.send_webhook(deal.webhook_url, {'event': 'funds.released', 'deal_code': deal.deal_code, 'amount': str(deal.amount), 'status': 'RELEASED'})

    @classmethod
    def notify_dispute_opened(cls, deal):
        ctx = {'deal_code': deal.deal_code}
        msg = cls.TEMPLATES['dispute_opened']['sms'].format(**ctx)
        if deal.merchant.phone:
            cls.send_sms(deal.merchant.phone, msg)
        if deal.buyer_phone:
            cls.send_sms(deal.buyer_phone, msg)
