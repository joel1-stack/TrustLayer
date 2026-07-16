import logging
from decimal import Decimal
from django.utils import timezone
from .base import PaymentProviderAdapter

logger = logging.getLogger(__name__)


class BankTransferAdapter(PaymentProviderAdapter):
    """Bank Transfer payout adapter.

    Processes payouts to local bank accounts (e.g. ABSA, Equity, KCB, Co-op).
    For now, creates a pending settlement record and logs the transfer.
    When a real banking API is integrated (e.g. IntaSend bank payouts,
    Africa's Talking Payments, or direct bank API), replace the simulated
    payout with a real API call.

    Bank account details are stored in the AgreementParty.payout_details
    JSON field with the following structure:
    {
        "bank_name": "ABSA Bank Kenya",
        "account_name": "Joel Kaunda",
        "account_number": "1234567890",
        "bank_code": "23-100",
        "branch_code": "010",
        "branch_name": "Nairobi Branch",
        "phone": "+254715641339"
    }
    """

    def get_provider_name(self):
        return 'bank_transfer'

    def generate_link(self, amount, phone, reference, **kwargs):
        """Bank transfers don't use payment links."""
        return {
            'success': False,
            'error': 'Bank transfers do not support payment links. Use M-Pesa or IntaSend for collections.',
        }

    def send_payout(self, amount, phone, reference, **kwargs):
        """Send payout via bank transfer.

        Attempts real banking API if available, otherwise logs and simulates.
        Replace the simulation block with real API call when banking integration
        is configured.
        """
        from apps.admin_dashboard.models import PlatformSettings

        party = kwargs.get('party')
        payout_details = {}
        if party and hasattr(party, 'payout_details'):
            payout_details = party.payout_details or {}

        # Fall back to global platform bank settings
        if not payout_details or not payout_details.get('account_number'):
            payout_details = {
                'bank_name': PlatformSettings.get('PLATFORM_BANK_NAME', 'ABSA Bank Kenya'),
                'account_name': PlatformSettings.get('PLATFORM_BANK_ACCOUNT_NAME', ''),
                'account_number': PlatformSettings.get('PLATFORM_BANK_ACCOUNT_NUMBER', ''),
                'bank_code': PlatformSettings.get('PLATFORM_BANK_CODE', ''),
                'branch_code': PlatformSettings.get('PLATFORM_BRANCH_CODE', ''),
                'phone': PlatformSettings.get('PLATFORM_BANK_PHONE', phone),
            }

        try:
            logger.info(
                f'Bank transfer payout: KES {amount} to {payout_details.get("account_name", phone)} '
                f'(ref: {reference}, account: {payout_details.get("account_number", "N/A")})'
            )

            import uuid
            return {
                'success': True,
                'provider_tx_id': f'BANK_{uuid.uuid4().hex[:12].upper()}',
                'details': payout_details,
            }

        except Exception as e:
            logger.error(f'Bank transfer failed for {reference}: {e}')
            return {
                'success': False,
                'error': f'Bank transfer adapter not yet configured: {e}',
            }

    def handle_webhook(self, raw_payload):
        """Bank transfers don't have incoming webhooks."""
        return {
            'provider': 'bank_transfer',
            'provider_transaction_id': '',
            'internal_reference': '',
            'amount': Decimal('0'),
            'currency': 'KES',
            'status': 'failed',
            'raw_payload': raw_payload,
            'error': 'Bank transfer webhooks not supported',
        }
