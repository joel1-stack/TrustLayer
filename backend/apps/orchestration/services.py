"""
Orchestration Engine — the conductor.

Flow:
  1. Developer creates agreement → CREATED → notify developer
  2. Developer requests payment link → generate via adapter → SUBMITTED
  3. Payment provider sends webhook → verify → AVAILABLE → Ledger → HELD
  4. Conditions met → READY → notify developer
  5. Trigger settlement → send payouts via adapter → SETTLING
  6. All payouts confirmed → SETTLED → notify developer
  7. Payout failures → FAILED → RETRYING → FAILED_PERMANENT
"""

import logging
from apps.state_machine.services import StateMachine
from apps.ledger.services import LedgerService
from apps.settlements.services import SettlementService
from apps.conditions.services import ConditionService
from apps.notifications.services import NotificationService

logger = logging.getLogger(__name__)


class Orchestrator:

    @staticmethod
    def on_agreement_created(agreement):
        NotificationService.on_agreement_created(agreement)
        return agreement

    @staticmethod
    def on_payment_link_generated(agreement, payment_url='', ip_address=None):
        if agreement.status == 'CREATED':
            kyc_ok = StateMachine.validate_kyc(agreement)
            if not kyc_ok and agreement.amount >= 50000:
                StateMachine.transition(
                    agreement, 'PENDING_KYC',
                    triggered_by='orchestrator',
                    actor_role='system',
                    channel='api',
                    ip_address=ip_address,
                    trigger_reason='kyc_required',
                    reason=f'KYC verification required for amount {agreement.amount}',
                )
                NotificationService.on_kyc_required(agreement)
                return None
            StateMachine.transition(
                agreement, 'CONFIRMED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='api',
                ip_address=ip_address,
                reason='Validation passed, generating payment link',
            )
        transition = StateMachine.transition(
            agreement, 'SUBMITTED',
            triggered_by='orchestrator',
            actor_role='system',
            channel='api',
            ip_address=ip_address,
            reason=f'Payment link generated: {payment_url}',
            evidence={'payment_url': payment_url}
        )
        NotificationService.on_payment_submitted(agreement, payment_url=payment_url)
        return transition

    @staticmethod
    def on_payment_collected(agreement, amount, reference='', phone='', ip_address=None):
        if agreement.status != 'SUBMITTED' and agreement.status != 'PENDING':
            logger.warning(f"Payment webhook for {agreement.agreement_id} but state is {agreement.status}")
            return None

        # If coming from SUBMITTED, first transition to PENDING (13000)
        if agreement.status == 'SUBMITTED':
            StateMachine.transition(
                agreement, 'PENDING',
                triggered_by='orchestrator',
                actor_role='provider_webhook',
                channel='webhook',
                ip_address=ip_address,
                provider_ref=reference,
                trigger_reason='payment_pending',
                reason=f'Provider acknowledged payment processing (ref: {reference})',
                evidence={'provider_ref': reference}
            )
        
        entry = LedgerService.credit(
            agreement, amount,
            reference=reference,
            description=f'Payment collected via provider ref {reference}',
            metadata={'phone': phone, 'provider_ref': reference}
        )

        from apps.agreements.services import AgreementService
        splits = AgreementService.calculate_splits(agreement)

        split_entries = []
        for split in splits:
            party = split['party']
            split_amount = split['amount']
            if split_amount > 0:
                se = LedgerService.credit(
                    agreement, split_amount,
                    party=party,
                    reference=f'split_{reference}',
                    description=f'Revenue split: {split_amount} to {party.name} ({party.role})',
                )
                split_entries.append(se)

        # Now transition to AVAILABLE (14000)
        StateMachine.transition(
            agreement, 'AVAILABLE',
            triggered_by='orchestrator',
            actor_role='provider_webhook',
            channel='webhook',
            ip_address=ip_address,
            provider_ref=reference,
            trigger_reason='payment_collected',
            reason=f'Payment of {amount} collected (ref: {reference})',
            evidence={'ledger_entry': entry.entry_id, 'reference': reference, 'splits': len(split_entries)}
        )

        NotificationService.on_payment_collected(agreement, amount)

        has_conditions = agreement.conditions.filter(required=True).exists()

        if has_conditions:
            StateMachine.transition(
                agreement, 'HELD',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                trigger_reason='awaiting_conditions',
                reason='Payment collected, awaiting conditions',
            )
        else:
            StateMachine.transition(
                agreement, 'READY',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                trigger_reason='no_conditions',
                reason='No conditions required, proceeding to settlement',
            )
            NotificationService.on_agreement_ready(agreement)

        return entry

    @staticmethod
    def on_condition_met(agreement, condition):
        NotificationService.on_condition_met(agreement, condition)

        if ConditionService.are_all_required_met(agreement):
            StateMachine.transition(
                agreement, 'READY',
                triggered_by='orchestrator',
                actor_role='system',
                channel='api',
                reason='All required conditions satisfied',
                evidence={'condition': condition.condition_id}
            )
            NotificationService.on_agreement_ready(agreement)
            return True
        return False

    @staticmethod
    def trigger_settlement(agreement):
        if agreement.status != 'READY':
            raise ValueError(f"Agreement {agreement.agreement_id} is not READY (currently {agreement.status})")

        StateMachine.transition(
            agreement, 'SETTLING',
            triggered_by='orchestrator',
            actor_role='system',
            channel='api',
            reason='Triggering settlement for all parties'
        )

        parties = agreement.parties.all()
        settlements = []
        settlement_ids = []
        all_succeeded = True
        any_succeeded = False

        for party in parties:
            balance = LedgerService.get_balance(party)
            if balance > 0:
                provider = party.payout_method or 'bank_transfer'
                settlement = SettlementService.settle_party(
                    agreement, party, balance, provider
                )
                settlements.append(settlement)
                settlement_ids.append(settlement.settlement_id)

                LedgerService.debit(
                    agreement, balance,
                    party=party,
                    reference=settlement.settlement_id,
                    description=f'Settled to {party.name} via {provider}'
                )

                if settlement.status == 'COMPLETED':
                    any_succeeded = True
                else:
                    all_succeeded = False

        NotificationService.on_settlement_started(agreement, settlements=settlement_ids)

        for settlement in settlements:
            if settlement.status == 'COMPLETED':
                NotificationService.on_settlement_completed(agreement, settlement)
            elif settlement.status in ('FAILED', 'RETRYING'):
                NotificationService.on_settlement_failed(agreement, settlement)

        if all_succeeded and settlements:
            StateMachine.transition(
                agreement, 'SETTLED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                trigger_reason='all_settlements_completed',
                reason='All settlements completed',
                evidence={'settlements': settlement_ids}
            )
            NotificationService.on_agreement_settled(agreement)
        elif any_succeeded and not all_succeeded:
            StateMachine.transition(
                agreement, 'PARTIALLY_SETTLED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                reason='Some settlements completed, some failed',
                evidence={'settlements': settlement_ids, 'failed': [s.settlement_id for s in settlements if s.status != 'COMPLETED']}
            )
        else:
            StateMachine.transition(
                agreement, 'FAILED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                reason='All settlements failed',
                evidence={'settlements': settlement_ids}
            )

        return settlements
