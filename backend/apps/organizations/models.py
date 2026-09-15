import uuid
from django.db import models


class Organization(models.Model):
    class Type(models.TextChoices):
        BANK = 'BANK', 'Bank'
        TELCO = 'TELCO', 'Telco'
        ECOMMERCE = 'ECOMMERCE', 'E-Commerce'
        INSURANCE = 'INSURANCE', 'Insurance'
        UTILITY = 'UTILITY', 'Utility'
        SACCO = 'SACCO', 'SACCO'
        GOVERNMENT = 'GOVERNMENT', 'Government'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        PENDING = 'PENDING', 'Pending'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    class IntegrationMode(models.TextChoices):
        EMBEDDED = 'EMBEDDED', 'Embedded (Widget/Deep Link)'
        STANDALONE = 'STANDALONE', 'Standalone (TrustLayer Portal)'
        API = 'API', 'API Only'

    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=50)
    org_type = models.CharField(max_length=20, choices=Type.choices, default=Type.OTHER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    integration_mode = models.CharField(max_length=20, choices=IntegrationMode.choices, default=IntegrationMode.EMBEDDED)

    # Branding
    brand_color = models.CharField(max_length=7, default='#FF5522')
    logo_url = models.URLField(blank=True, default='')

    # Integration
    webhook_url = models.URLField(blank=True, default='', help_text='POST case updates here')
    api_key = models.CharField(max_length=128, blank=True, default='', help_text='Partner API key for authentication')
    supported_intents = models.JSONField(default=list, blank=True, help_text='Case types this org supports')
    supported_channels = models.JSONField(default=list, blank=True, help_text='Entry channels: WEB, MOBILE, API, VOICE, SMS, WIDGET')

    # SIM Detection (for telcos)
    mcc_mnc = models.JSONField(default=list, blank=True, help_text='MCC/MNC codes e.g. ["63902"] for Safaricom Kenya')

    # Metadata
    contact_email = models.EmailField(blank=True, default='')
    contact_phone = models.CharField(max_length=20, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.slug})"
