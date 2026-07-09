"""
Orchestration Engine — the conductor.

Flow:
  1. Developer creates agreement → CREATED → notify developer
  2. Developer requests payment link → generate via adapter → PAYMENT_PENDING
  3. Payment provider sends webhook → verify → COLLECTED → Ledger → WAITING
  4. Conditions met → READY → notify developer
  5. Trigger settlement → send payouts via adapter → SETTLING
  6. All payouts confirmed → SETTLED → notify developer
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
        """Step 1: Agreement created → notify → move to CREATED"""
        NotificationService.on_agreement_created(agreement)
        return agreement

    @staticmethod
    def on_payment_link_generated(agreement, payment_url=''):
        """Step 1.5: Payment link generated → PAYMENT_PENDING → notify developer"""
        transition = StateMachine.transition(
            agreement, 'PAYMENT_PENDING',
            triggered_by='orchestrator',
            reason=f'Payment link generated: {payment_url}',
            evidence={'payment_url': payment_url}
        )
        NotificationService.on_payment_pending(agreement, payment_url=payment_url)
        return transition

    @staticmethod
    def on_payment_collected(agreement, amount, reference='', phone=''):
        """Step 2: Incoming webhook says payment completed → COLLECTED → Ledger → WAITING"""

        # Verify state is PAYMENT_PENDING
        if agreement.status != 'PAYMENT_PENDING':
            logger.warning(f"Payment webhook for {agreement.agreement_id} but state is {agreement.status}")
            return None

        # Credit the agreement ledger (total received)
        entry = LedgerService.credit(
            agreement, amount,
            reference=reference,
            description=f'Payment collected via provider ref {reference}',
            metadata={'phone': phone, 'provider_ref': reference}
        )

        # Compute splits and credit each party's ledger account
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

        # Move state: PAYMENT_PENDING → COLLECTED
        StateMachine.transition(
            agreement, 'COLLECTED',
            triggered_by='orchestrator',
            reason=f'Payment of {amount} collected (ref: {reference})',
            evidence={'ledger_entry': entry.entry_id, 'reference': reference, 'splits': len(split_entries)}
        )

        # Notify developer
        NotificationService.on_payment_collected(agreement, amount)

        # Check if there are required conditions
        has_conditions = agreement.conditions.filter(required=True).exists()

        if has_conditions:
            # Escrow flow: wait for conditions
            StateMachine.transition(
                agreement, 'WAITING',
                triggered_by='orchestrator',
                reason='Payment collected, awaiting conditions',
            )
        else:
            # Immediate split: no waiting, go straight to READY
            StateMachine.transition(
                agreement, 'READY',
                triggered_by='orchestrator',
                reason='Immediate split — no conditions required',
            )
            NotificationService.on_agreement_ready(agreement)

        return entry

    @staticmethod
    def on_condition_met(agreement, condition):
        """Step 3: Condition met → check if all ready → READY"""
        NotificationService.on_condition_met(agreement, condition)

        if ConditionService.are_all_required_met(agreement):
            StateMachine.transition(
                agreement, 'READY',
                triggered_by='orchestrator',
                reason='All required conditions satisfied',
                evidence={'condition': condition.condition_id}
            )
            NotificationService.on_agreement_ready(agreement)
            return True
        return False

    @staticmethod
    def trigger_settlement(agreement):
        """Step 4: Agreement READY → settle each party → SETTLED"""
        if agreement.status != 'READY':
            raise ValueError(f"Agreement {agreement.agreement_id} is not READY (currently {agreement.status})")

        StateMachine.transition(
            agreement, 'SETTLING',
            triggered_by='orchestrator',
            reason='Triggering settlement for all parties'
        )

        parties = agreement.parties.all()
        settlements = []
        settlement_ids = []

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

        NotificationService.on_settlement_started(agreement, settlements=settlement_ids)

        for settlement in settlements:
            NotificationService.on_settlement_completed(agreement, settlement)

        StateMachine.transition(
            agreement, 'SETTLED',
            triggered_by='orchestrator',
            reason='All settlements completed',
            evidence={'settlements': settlement_ids}
        )

        NotificationService.on_agreement_settled(agreement)

        return settlements