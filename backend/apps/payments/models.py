from django.db import models

class PaymentTransaction(models.Model):
    transaction_id = models.CharField(max_length=24, unique=True, editable=False)
    agreement = models.ForeignKey('agreements.Agreement', on_delete=models.CASCADE, related_name='payment_transactions')
    provider = models.CharField(max_length=32, help_text='intasend, mpesa, stripe')
    provider_tx_id = models.CharField(max_length=128, blank=True, default='')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    phone = models.CharField(max_length=32, blank=True, default='')
    payment_url = models.URLField(blank=True, default='')
    status = models.CharField(max_length=16, default='pending', help_text='pending, completed, failed')
    reference = models.CharField(max_length=128, blank=True, default='', help_text='Internal reference (agreement_id)')
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payment_transactions'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            import secrets, string
            self.transaction_id = 'PAY' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_id} {self.status} {self.amount}"


class WebhookEvent(models.Model):
    """Incoming webhook from payment provider."""
    event_id = models.CharField(max_length=24, unique=True, editable=False)
    provider = models.CharField(max_length=32)
    provider_event_id = models.CharField(max_length=128, blank=True, default='')
    raw_body = models.JSONField(default=dict, blank=True)
    signature_valid = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webhook_events'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.event_id:
            import secrets, string
            self.event_id = 'WH' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event_id} {self.provider} processed={self.processed}"