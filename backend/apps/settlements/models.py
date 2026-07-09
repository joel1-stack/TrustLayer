from django.db import models

class Settlement(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        RETRYING = 'RETRYING', 'Retrying'
    
    class Provider(models.TextChoices):
        MPESA_B2C = 'mpesa_b2c', 'M-Pesa B2C'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        INTASEND = 'intasend', 'IntaSend'
        STRIPE = 'stripe', 'Stripe'
    
    settlement_id = models.CharField(max_length=24, unique=True, editable=False)
    agreement = models.ForeignKey('agreements.Agreement', on_delete=models.CASCADE, related_name='settlements')
    party = models.ForeignKey('agreements.AgreementParty', on_delete=models.CASCADE, related_name='settlements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    provider = models.CharField(max_length=16, choices=Provider.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    
    # Provider details
    provider_tx_id = models.CharField(max_length=128, blank=True, default='')
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Retry
    retry_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'settlements'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.settlement_id:
            import secrets, string
            self.settlement_id = 'STL' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.settlement_id} {self.status} {self.amount} → {self.party.name}"
