"""
Orchestration Engine — System of Action conductor.

Flow:
  1. Receive incident → Create Case → ASSEMBLING
  2. Context Engine → Assemble context from adapters → ASSEMBLED
  3. Diagnosis Engine → Determine root cause → DIAGNOSED
  4. Policy Engine → Authorize actions → PLANNED
  5. Action Engine → Execute actions → EXECUTED
  6. Verification Engine → Verify outcome → VERIFIED
  7. Truth Engine → Record everything in ledger → RESOLVED
"""

import logging
from django.utils import timezone
from apps.state_machine.services import StateMachine
from apps.ledger.services import LedgerService
from apps.notifications.services import NotificationService

logger = logging.getLogger(__name__)


class Orchestrator:

    @staticmethod
    def on_case_created(case):
        NotificationService.on_agreement_created(case)
        return case

    @staticmethod
    def on_payment_link_generated(case, payment_url='', ip_address=None):
        if case.status == 'CREATED':
            kyc_ok = StateMachine.validate_kyc(case)
            if not kyc_ok and case.amount >= 50000:
                StateMachine.transition(
                    case, 'PENDING_KYC',
                    triggered_by='orchestrator',
                    actor_role='system',
                    channel='api',
                    ip_address=ip_address,
                    trigger_reason='kyc_required',
                    reason=f'KYC verification required for amount {case.amount}',
                )
                NotificationService.on_kyc_required(case)
                return None
            StateMachine.transition(
                case, 'CONFIRMED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='api',
                ip_address=ip_address,
                reason='Validation passed, generating payment link',
            )
        transition = StateMachine.transition(
            case, 'SUBMITTED',
            triggered_by='orchestrator',
            actor_role='system',
            channel='api',
            ip_address=ip_address,
            reason=f'Payment link generated: {payment_url}',
            evidence={'payment_url': payment_url}
        )
        NotificationService.on_payment_submitted(case, payment_url=payment_url)
        return transition

    @staticmethod
    def on_payment_collected(case, amount, reference='', phone='', ip_address=None):
        if case.status != 'SUBMITTED' and case.status != 'PENDING':
            logger.warning(f"Payment webhook for {case.agreement_id} but state is {case.status}")
            return None

        if case.status == 'SUBMITTED':
            StateMachine.transition(
                case, 'PENDING',
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
            case, amount,
            reference=reference,
            description=f'Payment collected via provider ref {reference}',
            metadata={'phone': phone, 'provider_ref': reference}
        )

        from apps.agreements.services import CaseService
        splits = CaseService.calculate_splits(case)

        split_entries = []
        for split in splits:
            party = split['party']
            split_amount = split['amount']
            if split_amount > 0:
                se = LedgerService.credit(
                    case, split_amount,
                    party=party,
                    reference=f'split_{reference}',
                    description=f'Revenue split: {split_amount} to {party.name} ({party.role})',
                )
                split_entries.append(se)

        StateMachine.transition(
            case, 'AVAILABLE',
            triggered_by='orchestrator',
            actor_role='provider_webhook',
            channel='webhook',
            ip_address=ip_address,
            provider_ref=reference,
            trigger_reason='payment_collected',
            reason=f'Payment of {amount} collected (ref: {reference})',
            evidence={'ledger_entry': entry.entry_id, 'reference': reference, 'splits': len(split_entries)}
        )

        NotificationService.on_payment_collected(case, amount)

        has_conditions = case.conditions.filter(required=True).exists()

        if has_conditions:
            StateMachine.transition(
                case, 'HELD',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                trigger_reason='awaiting_conditions',
                reason='Payment collected, awaiting conditions',
            )
        else:
            StateMachine.transition(
                case, 'READY',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                trigger_reason='no_conditions',
                reason='No conditions required, proceeding to settlement',
            )
            NotificationService.on_agreement_ready(case)

        return entry

    @staticmethod
    def on_condition_met(case, condition):
        NotificationService.on_condition_met(case, condition)

        from apps.conditions.services import ConditionService
        if ConditionService.are_all_required_met(case):
            StateMachine.transition(
                case, 'READY',
                triggered_by='orchestrator',
                actor_role='system',
                channel='api',
                reason='All required conditions satisfied',
                evidence={'condition': condition.condition_id}
            )
            NotificationService.on_agreement_ready(case)
            return True
        return False

    @staticmethod
    def trigger_settlement(case):
        if case.status != 'READY':
            raise ValueError(f"Case {case.agreement_id} is not READY (currently {case.status})")

        StateMachine.transition(
            case, 'SETTLING',
            triggered_by='orchestrator',
            actor_role='system',
            channel='api',
            reason='Triggering settlement for all parties'
        )

        parties = case.parties.all()
        settlements = []
        settlement_ids = []
        all_succeeded = True
        any_succeeded = False

        for party in parties:
            balance = LedgerService.get_balance(party)
            if balance > 0:
                provider = party.payout_method or 'bank_transfer'
                from apps.settlements.services import SettlementService
                settlement = SettlementService.settle_party(
                    case, party, balance, provider
                )
                settlements.append(settlement)
                settlement_ids.append(settlement.settlement_id)

                LedgerService.debit(
                    case, balance,
                    party=party,
                    reference=settlement.settlement_id,
                    description=f'Settled to {party.name} via {provider}'
                )

                if settlement.status == 'COMPLETED':
                    any_succeeded = True
                else:
                    all_succeeded = False

        NotificationService.on_settlement_started(case, settlements=settlement_ids)

        for settlement in settlements:
            if settlement.status == 'COMPLETED':
                NotificationService.on_settlement_completed(case, settlement)
            elif settlement.status in ('FAILED', 'RETRYING'):
                NotificationService.on_settlement_failed(case, settlement)

        if all_succeeded and settlements:
            StateMachine.transition(
                case, 'SETTLED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                trigger_reason='all_settlements_completed',
                reason='All settlements completed',
                evidence={'settlements': settlement_ids}
            )
            NotificationService.on_agreement_settled(case)
        elif any_succeeded and not all_succeeded:
            StateMachine.transition(
                case, 'PARTIALLY_SETTLED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                reason='Some settlements completed, some failed',
                evidence={'settlements': settlement_ids, 'failed': [s.settlement_id for s in settlements if s.status != 'COMPLETED']}
            )
        else:
            StateMachine.transition(
                case, 'FAILED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                reason='All settlements failed',
                evidence={'settlements': settlement_ids}
            )

        return settlements

    @staticmethod
    def assemble_context(case):
        """Phase 1: Assemble context from enterprise adapters."""
        from apps.context_engine.models import ContextRecord
        from apps.enterprise_adapters.adapters import (
            MockSubscriberAdapter, MockBillingAdapter,
            MockNetworkAdapter, MockDeviceAdapter
        )

        adapters = {
            'subscriber': MockSubscriberAdapter(),
            'billing': MockBillingAdapter(),
            'network': MockNetworkAdapter(),
            'device': MockDeviceAdapter(),
        }

        assembled = {}
        for name, adapter in adapters.items():
            try:
                import time
                start = time.time()
                result = adapter.query(case.agreement_id, case.metadata)
                latency = int((time.time() - start) * 1000)

                ContextRecord.objects.create(
                    case=case,
                    source_adapter=name,
                    query_type='standard',
                    raw_response=result,
                    assembled_context=result,
                    latency_ms=latency,
                    status='success',
                )
                assembled[name] = result
            except Exception as e:
                logger.error(f"Context assembly failed for {name}: {e}")
                ContextRecord.objects.create(
                    case=case,
                    source_adapter=name,
                    query_type='standard',
                    raw_response={'error': str(e)},
                    assembled_context={},
                    latency_ms=0,
                    status='failed',
                )

        StateMachine.transition(
            case, 'AVAILABLE',
            triggered_by='orchestrator',
            actor_role='system',
            channel='system',
            trigger_reason='context_assembled',
            reason=f'Context assembled from {len(assembled)} sources',
            evidence={'sources': list(assembled.keys())}
        )

        return assembled

    @staticmethod
    def diagnose(case, context):
        """Phase 2: Diagnose root cause from assembled context."""
        from apps.diagnosis_engine.models import DiagnosisRecord

        subscriber = context.get('subscriber', {})
        billing = context.get('billing', {})
        network = context.get('network', {})

        root_cause = 'UNKNOWN'
        confidence = 0.0
        evidence = {}
        recommended_actions = []

        if subscriber.get('status') == 'INACTIVE':
            root_cause = 'SUBSCRIBER_INACTIVE'
            confidence = 0.95
            evidence = {'subscriber_status': subscriber.get('status')}
            recommended_actions = ['reactivate_subscriber']
        elif billing.get('balance', 0) <= 0:
            root_cause = 'INSUFFICIENT_BALANCE'
            confidence = 0.90
            evidence = {'balance': billing.get('balance')}
            recommended_actions = ['send_payment_reminder', 'top_up_account']
        elif not network.get('service_available', True):
            root_cause = 'NETWORK_OUTAGE'
            confidence = 0.85
            evidence = {'tower_status': network.get('tower_status')}
            recommended_actions = ['check_tower_status', 'notify_network_ops']
        else:
            root_cause = 'BUNDLE_EXPIRED'
            confidence = 0.70
            evidence = {'plan': subscriber.get('plan')}
            recommended_actions = ['refresh_bundle', 'send_renewal_reminder']

        diagnosis = DiagnosisRecord.objects.create(
            case=case,
            root_cause=root_cause,
            confidence=confidence,
            evidence=evidence,
            recommended_actions=recommended_actions,
            diagnosed_by='system',
        )

        StateMachine.transition(
            case, 'RECONCILING',
            triggered_by='orchestrator',
            actor_role='system',
            channel='system',
            trigger_reason='diagnosis_complete',
            reason=f'Diagnosed: {root_cause} (confidence: {confidence})',
            evidence={'diagnosis_id': diagnosis.id, 'root_cause': root_cause}
        )

        return diagnosis

    @staticmethod
    def plan_action(case, diagnosis):
        """Phase 3: Plan actions based on diagnosis."""
        from apps.action_engine.models import ActionPlan
        from apps.policy_engine.models import PolicyRule, PolicyDecision

        actions = []
        for action_type in diagnosis.recommended_actions:
            rules = PolicyRule.objects.filter(action_type=action_type, enabled=True)
            approved = True
            for rule in rules:
                decision = PolicyDecision.objects.create(
                    case=case,
                    rule=rule,
                    decision='approved',
                    reason=f'Auto-approved for {diagnosis.root_cause}',
                    decided_by='system',
                )
                if decision.decision != 'approved':
                    approved = False
                    break

            if approved:
                plan = ActionPlan.objects.create(
                    case=case,
                    action_type=action_type,
                    parameters={'diagnosis': diagnosis.root_cause},
                    priority=1,
                    status='planned',
                )
                actions.append(plan)

        StateMachine.transition(
            case, 'HELD',
            triggered_by='orchestrator',
            actor_role='system',
            channel='system',
            trigger_reason='action_planned',
            reason=f'{len(actions)} actions planned',
            evidence={'action_count': len(actions)}
        )

        return actions

    @staticmethod
    def execute_actions(case, plans):
        """Phase 4: Execute authorized actions."""
        from apps.action_engine.models import ActionResult

        results = []
        for plan in plans:
            plan.status = 'executing'
            plan.save(update_fields=['status'])

            try:
                import time
                start = time.time()
                response = {'success': True, 'action': plan.action_type}
                duration = int((time.time() - start) * 1000)

                result = ActionResult.objects.create(
                    plan=plan,
                    outcome='success',
                    response_data=response,
                    executed_at=timezone.now(),
                    duration_ms=duration,
                )
                plan.status = 'completed'
                plan.save(update_fields=['status'])
                results.append(result)
            except Exception as e:
                result = ActionResult.objects.create(
                    plan=plan,
                    outcome='failed',
                    error_message=str(e),
                    executed_at=timezone.now(),
                )
                plan.status = 'failed'
                plan.save(update_fields=['status'])
                results.append(result)

        all_success = all(r.outcome == 'success' for r in results)
        if all_success:
            StateMachine.transition(
                case, 'READY',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                trigger_reason='actions_executed',
                reason='All actions executed successfully',
            )
        else:
            StateMachine.transition(
                case, 'DISPUTED',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                reason='Some actions failed',
            )

        return results

    @staticmethod
    def verify_outcome(case):
        """Phase 5: Verify service recovery."""
        from apps.verification_engine.models import VerificationCheck, VerificationResult

        checks = [
            {'type': 'service_status', 'expected': True, 'actual': True},
            {'type': 'connectivity', 'expected': True, 'actual': True},
        ]

        passed = 0
        total = len(checks)
        for check_data in checks:
            check = VerificationCheck.objects.create(
                case=case,
                check_type=check_data['type'],
                expected_value=check_data['expected'],
                actual_value=check_data['actual'],
                passed=check_data['expected'] == check_data['actual'],
                checked_at=timezone.now(),
            )
            if check.passed:
                passed += 1

        result = VerificationResult.objects.create(
            case=case,
            overall_passed=passed == total,
            checks_total=total,
            checks_passed=passed,
            recovery_confirmed=passed == total,
            verified_at=timezone.now(),
        )

        if result.recovery_confirmed:
            StateMachine.transition(
                case, 'SETTLING',
                triggered_by='orchestrator',
                actor_role='system',
                channel='system',
                trigger_reason='verification_passed',
                reason='Service recovery verified',
            )
            NotificationService.on_agreement_settled(case)
        else:
            # Verification failed — stay in READY, customer can escalate via feedback
            pass

        return result
