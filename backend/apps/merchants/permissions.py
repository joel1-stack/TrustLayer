"""
TrustLayer Authentication & Permissions
"""
import hashlib
import hmac
from rest_framework import authentication, exceptions
from .models import Merchant


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authorization: Bearer <api_key>  OR  X-API-Key: <api_key>
    Used for: profile, dashboard, webhook logs.
    """
    def authenticate(self, request):
        # Support both Bearer token and X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY', '')
        if not api_key:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                api_key = parts[1]
        if not api_key:
            return None

        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        try:
            merchant = Merchant.objects.get(api_key_hash=api_key_hash, is_active=True)
            return (merchant, None)
        except Merchant.DoesNotExist:
            return None


class APISecretAuthentication(authentication.BaseAuthentication):
    """
    X-API-Secret header.
    Used for: session creation, key rotation.
    NEVER expose in frontend code.
    """
    def authenticate(self, request):
        api_secret = request.META.get('HTTP_X_API_SECRET', '')
        if not api_secret:
            return None

        secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()

        try:
            merchant = Merchant.objects.get(api_secret_hash=secret_hash, is_active=True)
            return (merchant, None)
        except Merchant.DoesNotExist:
            return None


class WebhookSignatureVerifier:
    """Verify incoming webhook HMAC-SHA256 signatures."""

    @staticmethod
    def verify(payload: bytes, signature: str, secret: str) -> bool:
        expected = hmac.new(secret.encode(), payload, 'sha256').hexdigest()
        return hmac.compare_digest(expected, signature)
