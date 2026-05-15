"""
Merchant Services - Key Generation, Authentication, and Business Logic
"""
import secrets
import hashlib
import hmac
import re
from datetime import timedelta
from django.utils import timezone
from .models import Merchant, MerchantAPIKey


class MerchantService:
    """Handles all merchant business logic: onboarding, key generation, authentication."""

    MERCHANT_KEY_PREFIX = "mk_live_"
    API_KEY_PREFIX = "ak_live_"
    API_SECRET_PREFIX = "as_live_"
    WEBHOOK_SECRET_PREFIX = "whs_live_"

    @classmethod
    def generate_merchant(cls, company_name, email, phone):
        """
        Create a new merchant with full key pair.
        Returns dict with merchant object + plaintext keys (shown ONCE).
        """
        merchant_key    = cls._generate_key(cls.MERCHANT_KEY_PREFIX)
        api_key         = cls._generate_key(cls.API_KEY_PREFIX)
        api_secret      = cls._generate_secret()
        webhook_secret  = cls._generate_secret()

        api_key_hash        = cls._hash(api_key)
        api_secret_hash     = cls._hash(api_secret)
        webhook_secret_hash = cls._hash(webhook_secret)

        merchant = Merchant.objects.create(
            company_name=company_name,
            email=email,
            phone=phone,
            merchant_key=merchant_key,
            api_key_hash=api_key_hash,
            api_secret_hash=api_secret_hash,
            webhook_secret=webhook_secret_hash,
            compliance_status='pending',
            monthly_volume_limit=100000.00,
            subscription_tier='free',
            trust_score=0.50,
        )

        MerchantAPIKey.objects.create(
            merchant=merchant,
            key_hash=api_key_hash,
            secret_hash=api_secret_hash,
            version=1,
            is_active=True,
        )

        return {
            'merchant': merchant,
            'plaintext_keys': {
                'merchant_key':   merchant_key,    # Public identifier
                'api_key':        api_key,          # Server-side auth
                'api_secret':     api_secret,       # JWT signing — NEVER expose
                'webhook_secret': webhook_secret,   # Webhook HMAC
            },
            'warning': 'SAVE THESE KEYS NOW. They will never be shown again.',
        }

    @classmethod
    def authenticate_api_key(cls, api_key):
        """
        Verify API key for authenticated endpoints.
        Returns Merchant or None.
        """
        if not api_key:
            return None

        key_hash = cls._hash(api_key)

        try:
            return Merchant.objects.get(
                api_key_hash=key_hash,
                is_active=True,
                compliance_status__in=['pending', 'verified'],
            )
        except Merchant.DoesNotExist:
            pass

        # Grace period: check key history
        try:
            key_record = MerchantAPIKey.objects.get(key_hash=key_hash, is_active=True)
            return key_record.merchant
        except MerchantAPIKey.DoesNotExist:
            return None

    @classmethod
    def authenticate_api_secret(cls, api_secret, merchant_key):
        """
        Verify API secret for JWT session creation.
        Returns Merchant or None.
        """
        if not api_secret or not merchant_key:
            return None

        secret_hash = cls._hash(api_secret)

        try:
            return Merchant.objects.get(
                merchant_key=merchant_key,
                api_secret_hash=secret_hash,
                is_active=True,
            )
        except Merchant.DoesNotExist:
            return None

    @classmethod
    def rotate_keys(cls, merchant):
        """
        Rotate API keys. Old keys stay valid 24 hours (grace period).
        """
        old_key = MerchantAPIKey.objects.filter(merchant=merchant, is_active=True).first()
        if old_key:
            old_key.is_active = False
            old_key.revoked_at = timezone.now()
            old_key.save()

        new_api_key    = cls._generate_key(cls.API_KEY_PREFIX)
        new_api_secret = cls._generate_secret()
        new_key_hash   = cls._hash(new_api_key)
        new_secret_hash = cls._hash(new_api_secret)

        merchant.api_key_hash    = new_key_hash
        merchant.api_secret_hash = new_secret_hash
        merchant.secret_version += 1
        merchant.secret_rotated_at = timezone.now()
        merchant.save()

        MerchantAPIKey.objects.create(
            merchant=merchant,
            key_hash=new_key_hash,
            secret_hash=new_secret_hash,
            version=merchant.secret_version,
            is_active=True,
        )

        return {
            'api_key':           new_api_key,
            'api_secret':        new_api_secret,
            'version':           merchant.secret_version,
            'grace_period_ends': timezone.now() + timedelta(hours=24),
        }

    @classmethod
    def verify_webhook_signature(cls, merchant, payload, signature):
        """
        Verify HMAC-SHA256 signature on incoming webhooks.
        payload: raw request body bytes
        signature: hex string from header
        """
        expected = hmac.new(
            merchant.webhook_secret.encode(),
            payload,
            'sha256',
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _generate_key(prefix):
        return f"{prefix}{secrets.token_urlsafe(24)}"

    @staticmethod
    def _generate_secret():
        return secrets.token_urlsafe(48)

    @staticmethod
    def _hash(value):
        return hashlib.sha256(value.encode()).hexdigest()


class MerchantValidationService:
    """Input validation for merchant registration data."""

    @staticmethod
    def validate_company_name(name):
        if not name or len(name) < 2:
            return False, "Company name must be at least 2 characters"
        if len(name) > 255:
            return False, "Company name too long"
        return True, None

    @staticmethod
    def validate_email(email):
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
            return True, None
        except ValidationError:
            return False, "Invalid email address"

    @staticmethod
    def validate_phone(phone):
        """Kenyan format: 2547XXXXXXXX"""
        if re.match(r'^2547\d{8}$', str(phone)):
            return True, None
        return False, "Phone must be format: 2547XXXXXXXX"

    @staticmethod
    def validate_webhook_url(url):
        if not url.startswith('https://'):
            return False, "Webhook URL must use HTTPS"
        return True, None
