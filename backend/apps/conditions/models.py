from django.db import models

class Condition(models.Model):
    class Type(models.TextChoices):
        BUYER_CONFIRMATION = 'buyer_confirmation', 'Buyer Confirmation'
        SELLER_CONFIRMATION = 'seller_confirmation', 'Seller Confirmation'
        TIMEOUT = 'timeout', 'Timeout'
        DOCUMENT_UPLOADED = 'document_uploaded', 'Document Uploaded'
        INSPECTION = 'inspection', 'Inspection Passed'
        ADMIN_APPROVAL = 'admin_approval', 'Admin Approval'
        CUSTOM_WEBHOOK = 'custom_webhook', 'Custom Webhook'
        PAYMENT_RECEIVED = 'payment_received', 'Payment Received'
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        MET = 'MET', 'Met'
        FAILED = 'FAILED', 'Failed'
        SKIPPED = 'SKIPPED', 'Skipped'
    
    condition_id = models.CharField(max_length=24, unique=True, editable=False)
    agreement = models.ForeignKey('agreements.Agreement', on_delete=models.CASCADE, related_name='conditions')
    condition_type = models.CharField(max_length=32, choices=Type.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    label = models.CharField(max_length=255, help_text='Human-readable description')
    required = models.BooleanField(default=True, help_text='Must be met for READY transition')
    order = models.IntegerField(default=0, help_text='Evaluation order')
    
    # Timeout support
    timeout_hours = models.IntegerField(null=True, blank=True, help_text='Auto-fail after N hours')
    timeout_at = models.DateTimeField(null=True, blank=True)
    
    # Evidence
    evidence = models.JSONField(default=dict, blank=True)
    met_by = models.CharField(max_length=128, blank=True, default='', help_text='Who/What triggered this')
    met_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conditions'
        ordering = ['order', 'created_at']
    
    def save(self, *args, **kwargs):
        if not self.condition_id:
            import secrets, string
            self.condition_id = 'CON' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.condition_id} [{self.condition_type}] {self.status}"
