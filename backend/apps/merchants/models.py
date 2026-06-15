from django.db import models
import uuid
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class Merchant(models.Model):
    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=255, blank=True)

    def set_password(self, raw):
        self.password = make_password(raw)

    def check_password(self, raw):
        if not self.password:
            return False
        return check_password(raw, self.password)
    
    # API Keys (the security foundation)
    merchant_key = models.CharField(max_length=255, unique=True)  # PUBLIC
    api_key_hash = models.CharField(max_length=255)               # PRIVATE (hashed)
    api_secret_hash = models.CharField(max_length=255)            # PRIVATE (hashed, for JWT)
    
    # Secret Rotation
    secret_version = models.IntegerField(default=1)
    secret_rotated_at = models.DateTimeField(null=True, blank=True)
    webhook_secret = models.CharField(max_length=255)             # For HMAC verification
    
    # Webhook & Redirect URLs
    webhook_url = models.URLField(max_length=500, blank=True)
    success_url = models.URLField(max_length=500, blank=True)
    failure_url = models.URLField(max_length=500, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    compliance_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('verified', 'Verified'),
            ('suspended', 'Suspended')
        ],
        default='pending'
    )
    
    # KYC
    kyc_submitted_at = models.DateTimeField(null=True, blank=True)
    kyc_documents = models.JSONField(default=dict, blank=True)
    
    # Limits & Scoring
    monthly_volume_limit = models.DecimalField(max_digits=15, decimal_places=2, default=100000.00)
    subscription_tier = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Free'),
            ('starter', 'Starter'),
            ('growth', 'Growth'),
            ('enterprise', 'Enterprise')
        ],
        default='free'
    )
    trust_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.50)
    total_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    dispute_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'merchants'
        indexes = [
            models.Index(fields=['merchant_key']),
            models.Index(fields=['email']),
            models.Index(fields=['compliance_status']),
        ]
    
    def __str__(self):
        return f"{self.company_name} ({self.merchant_key})"


class MerchantAPIKey(models.Model):
    """
    Tracks API key history for audit and rotation.
    """
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='api_keys')
    key_hash = models.CharField(max_length=255)
    secret_hash = models.CharField(max_length=255)
    version = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'merchant_api_keys'
        ordering = ['-version']