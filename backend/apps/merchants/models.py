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
    
    # Payout
    PAYOUT_METHOD_CHOICES = [
        ('phone', 'Phone (M-Pesa B2C)'),
        ('pochi', 'Pochi la Biashara'),
        ('till', 'Till Number (Coming Soon)'),
        ('bank', 'Bank Transfer (Coming Soon)'),
    ]
    payout_method = models.CharField(max_length=20, choices=PAYOUT_METHOD_CHOICES, default='phone')
    payout_account = models.CharField(max_length=100, blank=True, help_text='Phone number for B2C, till number, or bank account')
    payout_bank_name = models.CharField(max_length=100, blank=True, help_text='Bank name (required if method=bank)')
    payout_account_name = models.CharField(max_length=100, blank=True, help_text='Account holder name (required if method=bank)')

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


class Organization(models.Model):
    """
    Top-level entity. A company that owns one or more businesses.
    Can be an insurance company, event organizer, school, franchise, clinic, etc.
    """
    ORG_TYPES = [
        ('insurance', 'Insurance Company'),
        ('event', 'Event Organiser'),
        ('franchise', 'Franchise'),
        ('school', 'School / Education'),
        ('clinic', 'Clinic / Hospital'),
        ('laundry', 'Laundry / Cleaning'),
        ('retail', 'Retail / Shop'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    org_type = models.CharField(max_length=20, choices=ORG_TYPES, default='other')
    owner = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='organizations')
    kra_pin = models.CharField(max_length=20, blank=True, help_text='KRA PIN for tax compliance')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_org_type_display()})"


class SplitRule(models.Model):
    """
    Defines how payments are split between parties.
    E.g. 80% to merchant, 5% platform fee, 15% to partner.
    Applied automatically when a payment comes in.
    """
    SPLIT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='split_rules')
    name = models.CharField(max_length=255, help_text='E.g. "Platform fee", "Partner share"')
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPES, default='percentage')
    value = models.DecimalField(max_digits=8, decimal_places=2, help_text='Percentage (e.g. 5.00) or fixed amount (KES)')
    destination_account = models.CharField(max_length=255, blank=True, help_text='Where this split goes (wallet phone, bank ref, or "platform")')
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text='Higher priority processed first')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'split_rules'
        ordering = ['-priority']

    def __str__(self):
        if self.split_type == 'percentage':
            return f"{self.name}: {self.value}% of payment"
        return f"{self.name}: KES {self.value} per payment"


class Business(models.Model):
    """
    A store/location under an organization.
    E.g. "Westlands Branch", "CBD Store"
    """
    SETTLEMENT_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('instant', 'Instant'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='businesses')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, help_text='Business contact / M-Pesa receiving number')
    email = models.EmailField(blank=True)

    # KYC & Compliance
    kra_pin = models.CharField(max_length=20, blank=True)
    business_reg_number = models.CharField(max_length=50, blank=True, help_text='Certificate of registration')
    is_verified = models.BooleanField(default=False)

    # Bank / payout details
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_account_name = models.CharField(max_length=100, blank=True)

    # Settlement
    settlement_preference = models.CharField(
        max_length=10, choices=SETTLEMENT_CHOICES, default='instant'
    )

    # Cashier PIN (shared PIN for this business's cashiers)
    cashier_pin = models.CharField(max_length=6, blank=True, help_text='6-digit PIN for cashier login')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'businesses'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class CashierSession(models.Model):
    """
    Tracks cashier login sessions (PIN-based).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='cashier_sessions')
    pin_entered = models.CharField(max_length=6)
    is_active = models.BooleanField(default=True)
    logged_in_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'cashier_sessions'

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at