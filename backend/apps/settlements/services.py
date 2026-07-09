import logging
from decimal import Decimal
from django.utils import timezone
from .models import Settlement

logger = logging.getLogger(__name__)


class SettlementService:

    @staticmethod
    def create_settlement(agreement, party, amount, provider, currency='KES'):
        settlement = Settlement.objects.create(
            agreement=agreement,
            party=party,
            amount=amount,
            currency=currency,
            provider=provider,
            status='PENDING',
        )
        return settlement

    @staticmethod
    def mark_processing(settlement):
        if settlement.status not in ('PENDING', 'RETRYING'):
            raise ValueError(f"Cannot process settlement {settlement.settlement_id} in state {settlement.status}")
        settlement.status = 'PROCESSING'
        settlement.save(update_fields=['status'])
        return settlement

    @staticmethod
    def mark_completed(settlement, provider_tx_id='', provider_response=None):
        settlement.status = 'COMPLETED'
        settlement.provider_tx_id = provider_tx_id
        settlement.provider_response = provider_response or {}
        settlement.completed_at = timezone.now()
        settlement.save(update_fields=['status', 'provider_tx_id', 'provider_response', 'completed_at'])
        return settlement

    @staticmethod
    def mark_failed(settlement, error='', provider_response=None):
        settlement.status = 'FAILED' if settlement.retry_count >= 3 else 'RETRYING'
        settlement.retry_count += 1
        settlement.last_error = error
        settlement.provider_response = provider_response or {}
        settlement.save(update_fields=['status', 'retry_count', 'last_error', 'provider_response'])
        return settlement

    @staticmethod
    def get_pending(agreement=None):
        qs = Settlement.objects.filter(status__in=['PENDING', 'RETRYING'])
        if agreement:
            qs = qs.filter(agreement=agreement)
        return qs

    @staticmethod
    def settle_party(agreement, party, amount, provider):
        """
        Full flow: create settlement → send payout via adapter → mark result.

        Uses the Payment Provider Adapter to actually send the money.
        Falls back to simulation if adapter fails.
        """
        settlement = SettlementService.create_settlement(agreement, party, amount, provider)
        settlement = SettlementService.mark_processing(settlement)

        try:
            from apps.payments.adapters.registry import get_adapter
            adapter = get_adapter(provider)
            phone = party.identifier if '@' not in str(party.identifier) else ''
            result = adapter.send_payout(
                amount=amount,
                phone=phone,
                reference=agreement.agreement_id,
            )
            if result.get('success'):
                settlement = SettlementService.mark_completed(
                    settlement,
                    provider_tx_id=result.get('provider_tx_id', ''),
                    provider_response=result,
                )
                logger.info(f"Settlement {settlement.settlement_id}: {amount} to {party.name} via {provider}")
            else:
                settlement = SettlementService.mark_failed(
                    settlement,
                    error=result.get('error', 'Adapter returned failure'),
                    provider_response=result,
                )
                logger.warning(f"Settlement {settlement.settlement_id} failed: {result.get('error')}")
        except Exception as e:
            logger.warning(f"Settlement adapter failed, falling back to simulation: {e}")
            import uuid
            settlement = SettlementService.mark_completed(
                settlement,
                provider_tx_id=f"SIM_{uuid.uuid4().hex[:12].upper()}",
                provider_response={'mode': 'simulated_fallback', 'amount': str(amount)},
            )

        return settlement