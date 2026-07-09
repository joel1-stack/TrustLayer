import json
import logging
from django.utils import timezone
from .models import NotificationEvent

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    def notify(event, agreement, message='', channel='log', recipient='', metadata=None):
        notification = NotificationEvent.objects.create(
            agreement=agreement,
            event=event,
            channel=channel,
            recipient=recipient,
            message=message,
            metadata=metadata or {},
        )
        NotificationService._send(notification)
        # Also fire outgoing webhook to developer if they provided one
        if agreement.developer_webhook_url:
            NotificationService._fire_developer_webhook(agreement, event, metadata)
        return notification

    @staticmethod
    def _send(notification):
        notification.sent = True
        notification.sent_at = timezone.now()
        notification.save(update_fields=['sent', 'sent_at'])

    @staticmethod
    def _fire_developer_webhook(agreement, event, metadata=None):
        """Direction 1: TrustLayer → Developer (Outgoing).
        
        POSTs to the developer's webhook URL with event data.
        """
        payload = {
            'event': event,
            'agreement_id': agreement.agreement_id,
            'status': agreement.status,
            'amount': str(agreement.amount),
            'currency': agreement.currency,
            'title': agreement.title,
            'metadata': metadata or {},
            'timestamp': timezone.now().isoformat(),
        }
        url = agreement.developer_webhook_url
        try:
            import requests
            resp = requests.post(url, json=payload, timeout=10,
                                 headers={'User-Agent': 'TrustLayer/2.0'})
            if not resp.ok:
                logger.warning(f"Developer webhook {event} → {url} returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"Developer webhook {event} → {url} failed: {e}")

    @staticmethod
    def on_agreement_created(agreement):
        msg = f"Agreement {agreement.agreement_id} created: {agreement.title} ({agreement.amount} {agreement.currency})"
        NotificationService.notify('agreement.created', agreement, message=msg, channel='log')

    @staticmethod
    def on_payment_pending(agreement, payment_url=''):
        msg = f"Payment pending for {agreement.agreement_id}. Link: {payment_url}"
        NotificationService.notify('payment.pending', agreement, message=msg, channel='log',
                                   metadata={'payment_url': payment_url})

    @staticmethod
    def on_payment_collected(agreement, amount):
        msg = f"Payment of {amount} collected for agreement {agreement.agreement_id}"
        NotificationService.notify('payment.collected', agreement, message=msg, channel='log',
                                   metadata={'collected_amount': str(amount)})

    @staticmethod
    def on_condition_met(agreement, condition):
        msg = f"Condition '{condition.label}' met for agreement {agreement.agreement_id}"
        NotificationService.notify('condition.met', agreement, message=msg, channel='log',
                                   metadata={'condition': condition.condition_id})

    @staticmethod
    def on_agreement_ready(agreement):
        msg = f"Agreement {agreement.agreement_id} is READY — all conditions satisfied"
        NotificationService.notify('agreement.ready', agreement, message=msg, channel='log')

    @staticmethod
    def on_settlement_started(agreement, settlements=None):
        msg = f"Settlement started for {agreement.agreement_id}"
        NotificationService.notify('settlement.started', agreement, message=msg, channel='log',
                                   metadata={'settlements': settlements or []})

    @staticmethod
    def on_settlement_completed(agreement, settlement):
        msg = f"Settlement {settlement.settlement_id} completed: {settlement.amount} to {settlement.party.name}"
        NotificationService.notify('settlement.completed', agreement, message=msg, channel='log',
                                   metadata={'settlement': settlement.settlement_id})

    @staticmethod
    def on_agreement_settled(agreement):
        msg = f"Agreement {agreement.agreement_id} fully SETTLED"
        NotificationService.notify('agreement.settled', agreement, message=msg, channel='log')