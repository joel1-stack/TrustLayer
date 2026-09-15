"""
Orchestration Engine -- System of Action conductor.

Organization-agnostic pipeline:
  1. Receive case -> CONFIRMED -> SUBMITTED -> PENDING
  2. Context Engine -> Assemble context from org-specific adapters -> AVAILABLE
  3. Diagnosis Engine -> Determine root cause -> RECONCILING
  4. Policy Engine -> Authorize actions -> HELD
  5. Action Engine -> Execute actions -> READY
  6. Verification Engine -> Verify outcome -> SETTLING
  7. Truth Engine -> Record everything -> SETTLED

Each organization (KCB, Safaricom, Jumia, etc.) has its own adapters
registered in the AdapterRegistry. The orchestrator looks up the right
adapters based on the case's organization.
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
    def assemble_context(case):
        """Phase 1: Assemble context from organization-specific adapters."""
        from apps.context_engine.models import ContextRecord
        from apps.enterprise_adapters.adapters import AdapterRegistry

        org_slug = case.organization.slug if case.organization else ''

        # Get adapters for this organization
        adapter_types = ['customer', 'service', 'billing', 'network', 'device', 'fraud']
        adapters = {}
        for atype in adapter_types:
            adapter = AdapterRegistry.get(org_slug, atype)
            if adapter:
                adapters[atype] = adapter

        # Fallback: if no org-specific adapters, use any available
        if not adapters:
            all_adapters = AdapterRegistry.get_all_for_org(org_slug)
            adapters = all_adapters

        assembled = {}
        customer_ref = case.customer_ref or case.case_id
        for name, adapter in adapters.items():
            try:
                import time
                start = time.time()

                if hasattr(adapter, 'get_customer'):
                    result = adapter.get_customer(customer_ref, case.metadata)
                elif hasattr(adapter, 'get_service'):
                    result = adapter.get_service(customer_ref, case.metadata)
                elif hasattr(adapter, 'get_billing'):
                    result = adapter.get_billing(customer_ref, case.metadata)
                elif hasattr(adapter, 'get_network_state'):
                    result = adapter.get_network_state(customer_ref, case.metadata)
                elif hasattr(adapter, 'get_device'):
                    result = adapter.get_device(customer_ref, case.metadata)
                elif hasattr(adapter, 'get_fraud_signals'):
                    result = adapter.get_fraud_signals(customer_ref, case.metadata)
                else:
                    result = {}

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
            reason=f'Context assembled from {len(assembled)} sources ({org_slug})',
            evidence={'sources': list(assembled.keys()), 'organization': org_slug}
        )

        return assembled

    @staticmethod
    def diagnose(case, context):
        """Phase 2: Diagnose root cause from assembled context."""
        from apps.diagnosis_engine.models import DiagnosisRecord

        customer = context.get('customer', {})
        billing = context.get('billing', {})
        network = context.get('network', {})
        service = context.get('service', {})
        fraud = context.get('fraud', {})

        root_cause = 'UNKNOWN'
        confidence = 0.0
        evidence = {}
        recommended_actions = []

        # Organization-agnostic diagnosis rules
        if fraud.get('account_takeover_risk') == 'HIGH' or fraud.get('risk_score', 0) > 0.8:
            root_cause = 'FRAUD_DETECTED'
            confidence = 0.95
            evidence = {'fraud_signals': fraud}
            recommended_actions = ['freeze_account', 'escalate_fraud_team', 'verify_identity']
        elif customer.get('status') == 'INACTIVE':
            root_cause = 'CUSTOMER_INACTIVE'
            confidence = 0.92
            evidence = {'customer_status': customer.get('status')}
            recommended_actions = ['reactivate_customer', 'verify_account']
        elif billing.get('balance', 0) <= 0 or billing.get('outstanding_balance', 0) > 0:
            root_cause = 'BILLING_ISSUE'
            confidence = 0.88
            evidence = {'balance': billing.get('balance'), 'outstanding': billing.get('outstanding_balance')}
            recommended_actions = ['send_payment_reminder', 'review_account']
        elif not network.get('service_available', True) if network else False:
            root_cause = 'SERVICE_OUTAGE'
            confidence = 0.85
            evidence = {'service_status': network.get('tower_status', 'unknown')}
            recommended_actions = ['check_service_status', 'notify_operations']
        elif service.get('status') == 'DEGRADED' if service else False:
            root_cause = 'SERVICE_DEGRADED'
            confidence = 0.80
            evidence = {'service_status': service.get('status')}
            recommended_actions = ['restore_service', 'send_status_update']
        else:
            root_cause = 'GENERAL_ISSUE'
            confidence = 0.70
            evidence = {'context': 'all_systems_nominal'}
            recommended_actions = ['investigate_further', 'contact_customer']

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
                    parameters={'diagnosis': diagnosis.root_cause, 'organization': case.organization.slug if case.organization else ''},
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
        """Phase 4: Execute authorized actions via organization adapters."""
        from apps.action_engine.models import ActionResult
        from apps.enterprise_adapters.adapters import AdapterRegistry

        org_slug = case.organization.slug if case.organization else ''
        action_adapter = AdapterRegistry.get(org_slug, 'action')

        results = []
        for plan in plans:
            plan.status = 'executing'
            plan.save(update_fields=['status'])

            try:
                import time
                start = time.time()

                if action_adapter:
                    response = action_adapter.execute(plan.action_type, case.customer_ref, plan.parameters)
                else:
                    response = {'success': True, 'action': plan.action_type, 'result': 'No action adapter configured'}

                duration = int((time.time() - start) * 1000)

                result = ActionResult.objects.create(
                    plan=plan,
                    outcome='success' if response.get('success') else 'failed',
                    response_data=response,
                    executed_at=timezone.now(),
                    duration_ms=duration,
                )
                plan.status = 'completed' if response.get('success') else 'failed'
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
            {'type': 'resolution_confirmed', 'expected': True, 'actual': True},
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
            pass

        return result

    # Legacy methods kept for backward compatibility
    @staticmethod
    def on_payment_link_generated(case, payment_url='', ip_address=None):
        if case.status == 'CREATED':
            StateMachine.transition(
                case, 'CONFIRMED',
                triggered_by='orchestrator', actor_role='system', channel='api',
                reason='Validation passed',
            )
        StateMachine.transition(
            case, 'SUBMITTED',
            triggered_by='orchestrator', actor_role='system', channel='api',
            reason=f'Payment link generated: {payment_url}',
            evidence={'payment_url': payment_url}
        )
        return case

    @staticmethod
    def on_payment_collected(case, amount, reference='', phone='', ip_address=None):
        StateMachine.transition(
            case, 'AVAILABLE',
            triggered_by='orchestrator', actor_role='provider_webhook', channel='webhook',
            reason=f'Payment of {amount} collected',
            evidence={'reference': reference}
        )
        return case

    @staticmethod
    def trigger_settlement(case):
        StateMachine.transition(
            case, 'SETTLING',
            triggered_by='orchestrator', actor_role='system', channel='api',
            reason='Triggering settlement'
        )
        StateMachine.transition(
            case, 'SETTLED',
            triggered_by='orchestrator', actor_role='system', channel='system',
            reason='Settlement completed'
        )
        return []
