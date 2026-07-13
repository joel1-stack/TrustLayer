from django.db import models

class NotificationEvent(models.Model):
    class Event(models.TextChoices):
        AGREEMENT_CREATED = 'agreement.created', 'Agreement Created'
        PAYMENT_SUBMITTED = 'payment.submitted', 'Payment Submitted'
        PAYMENT_PENDING = 'payment.pending', 'Payment Pending'
        PAYMENT_COLLECTED = 'payment.collected', 'Payment Collected'
        PAYMENT_DECLINED = 'payment.declined', 'Payment Declined'
        CONDITION_MET = 'condition.met', 'Condition Met'
        AGREEMENT_HELD = 'agreement.held', 'Agreement Held'
        AGREEMENT_READY = 'agreement.ready', 'Agreement Ready'
        AGREEMENT_DISPUTED = 'agreement.disputed', 'Agreement Disputed'
        SETTLEMENT_STARTED = 'settlement.started', 'Settlement Started'
        SETTLEMENT_COMPLETED = 'settlement.completed', 'Settlement Completed'
        SETTLEMENT_FAILED = 'settlement.failed', 'Settlement Failed'
        AGREEMENT_SETTLED = 'agreement.settled', 'Agreement Settled'
        AGREEMENT_REVERSED = 'agreement.reversed', 'Agreement Reversed'
        AGREEMENT_REFUNDED = 'agreement.refunded', 'Agreement Refunded'
        AGREEMENT_CANCELLED = 'agreement.cancelled', 'Agreement Cancelled'
    
    event_id = models.CharField(max_length=24, unique=True, editable=False)
    agreement = models.ForeignKey('agreements.Agreement', on_delete=models.CASCADE, related_name='notifications')
    event = models.CharField(max_length=32, choices=Event.choices)
    channel = models.CharField(max_length=32, default='log', help_text='sms, email, webhook, push, log')
    recipient = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField(blank=True, default='')
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification_events'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.event_id:
            import secrets, string
            self.event_id = 'NOT' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.event_id} {self.event} sent={self.sent}"