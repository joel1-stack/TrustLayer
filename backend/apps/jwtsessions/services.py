"""
JWT Session Services - Token Creation, Validation, and Security
"""
import jwt
import secrets
import re
from datetime import timedelta
from django.utils import timezone
from .models import MerchantSession


class JWTSessionService:
    """
    Creates and validates scoped JWT payment tokens.

    Security model:
    - Merchant's api_secret (server-side only) signs the JWT
    - JWT goes to frontend — frontend can only consume, not create deals
    - Every token is stored in DB for revocation checking
    - One-time use, 15-minute expiry
    """

    ALGORITHM = 'HS256'
    DEFAULT_EXPIRY_MINUTES = 15

    @classmethod
    def create_session(cls, merchant, amount, description, customer_phone,
                       customer_email='', success_url='', failure_url='',
                       ip_address=None):
        """
        Create a scoped JWT session for payment initialization.

        Args:
            merchant:       Merchant object (authenticated via api_secret)
            amount:         Deal amount in KES (100 – 500,000)
            description:    What is being purchased
            customer_phone: Buyer's phone (2547XXXXXXXX)
            customer_email: Optional
            success_url:    Override merchant default
            failure_url:    Override merchant default
            ip_address:     Request IP for audit

        Returns:
            dict: session_token, checkout_url, expires_at, expires_in_seconds
        """
        if not cls._validate_amount(amount):
            raise ValueError("Amount must be between 100 and 500,000 KES")

        if not cls._validate_phone(customer_phone):
            raise ValueError("Phone must be format: 2547XXXXXXXX")

        now        = timezone.now()
        expires_at = now + timedelta(minutes=cls.DEFAULT_EXPIRY_MINUTES)
        session_id = secrets.token_urlsafe(16)

        payload = {
            # Standard JWT claims
            'jti': session_id,
            'iat': int(now.timestamp()),
            'exp': int(expires_at.timestamp()),

            # TrustLayer claims
            'merchant_id':     str(merchant.id),
            'merchant_key':    merchant.merchant_key,
            'amount':          float(amount),
            'currency':        'KES',
            'description':     description,
            'customer_phone':  customer_phone,
            'customer_email':  customer_email,
            'success_url':     success_url or merchant.success_url,
            'failure_url':     failure_url or merchant.failure_url,
            'ip_address':      ip_address,
            'version':         merchant.secret_version,
        }

        # Sign with merchant's hashed secret (not a global key)
        token = jwt.encode(payload, merchant.api_secret_hash, algorithm=cls.ALGORITHM)

        session = MerchantSession.objects.create(
            merchant=merchant,
            session_token=token,
            amount=amount,
            currency='KES',
            description=description,
            customer_phone=customer_phone,
            customer_email=customer_email,
            success_url=success_url or merchant.success_url,
            failure_url=failure_url or merchant.failure_url,
            expires_at=expires_at,
            used=False,
            ip_address=ip_address,
        )

        return {
            'session_token':      token,
            'checkout_url':       f'https://trustlayer.app/pay/{token}',
            'expires_at':         expires_at.isoformat(),
            'expires_in_seconds': cls.DEFAULT_EXPIRY_MINUTES * 60,
        }

    @classmethod
    def validate_token(cls, token):
        """
        Validate a JWT session token.

        Returns:
            dict: {valid, session, merchant, payload}

        Raises:
            ValueError with reason if invalid
        """
        try:
            session = MerchantSession.objects.select_related('merchant').get(session_token=token)
        except MerchantSession.DoesNotExist:
            raise ValueError("Token not found")

        if session.used:
            raise ValueError("Token already used")

        if session.is_expired():
            raise ValueError("Token expired")

        merchant = session.merchant

        try:
            payload = jwt.decode(token, merchant.api_secret_hash, algorithms=[cls.ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token signature")

        return {
            'valid':    True,
            'session':  session,
            'merchant': merchant,
            'payload':  payload,
        }

    @classmethod
    def consume_token(cls, token):
        """
        Mark token as used after successful payment initiation.
        Returns MerchantSession.
        """
        result = cls.validate_token(token)
        result['session'].mark_used()
        return result['session']

    @classmethod
    def revoke_token(cls, token):
        """Revoke a token before expiry (merchant cancellation)."""
        try:
            session = MerchantSession.objects.get(session_token=token)
            session.used = True
            session.save(update_fields=['used'])
            return True
        except MerchantSession.DoesNotExist:
            return False

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _validate_amount(amount):
        try:
            return 100 <= float(amount) <= 500000
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _validate_phone(phone):
        return bool(re.match(r'^2547\d{8}$', str(phone)))


class SessionAuditService:
    """Track and audit session usage."""

    @staticmethod
    def log_session_created(session, ip_address, user_agent=''):
        print(f"[AUDIT] Session {session.id} created for {session.merchant.merchant_key} from {ip_address}")

    @staticmethod
    def log_session_consumed(session, ip_address, provider='mpesa'):
        print(f"[AUDIT] Session {session.id} consumed via {provider} from {ip_address}")

    @staticmethod
    def get_merchant_sessions(merchant, limit=50):
        return MerchantSession.objects.filter(merchant=merchant).order_by('-created_at')[:limit]
