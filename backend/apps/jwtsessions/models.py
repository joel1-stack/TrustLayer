from django.db import models
import uuid
from django.utils import timezone

class MerchantSession(models.Model):
    """
    Scoped JWT session for payment initialization.
    Created by merchant backend, consumed by frontend.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey('merchants.Merchant', on_delete=models.CASCADE, related_name='jwt_sessions')
    
    # The JWT token (encrypted at rest)
    session_token = models.TextField()
    
    # Scope (what this token can do)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    description = models.CharField(max_length=500)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True)
    
    # Overrides (optional)
    success_url = models.URLField(max_length=500, blank=True)
    failure_url = models.URLField(max_length=500, blank=True)
    
    # Security
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # Audit
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'merchant_sessions'
        indexes = [
            models.Index(fields=['session_token']),
            models.Index(fields=['merchant', 'used']),
            models.Index(fields=['expires_at']),
        ]
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return not self.used and not self.is_expired()
    
    def mark_used(self):
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=['used', 'used_at'])