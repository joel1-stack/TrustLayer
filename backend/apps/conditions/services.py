from django.utils import timezone
from .models import Condition

class ConditionService:
    
    @staticmethod
    def add_condition(agreement, condition_type, label, required=True, order=0, timeout_hours=None):
        condition = Condition.objects.create(
            agreement=agreement,
            condition_type=condition_type,
            label=label,
            required=required,
            order=order,
            timeout_hours=timeout_hours,
            timeout_at=(timezone.now() + timezone.timedelta(hours=timeout_hours)) if timeout_hours else None,
        )
        return condition
    
    @staticmethod
    def mark_met(condition, met_by='system', evidence=None):
        if condition.status != 'PENDING':
            raise ValueError(f"Condition {condition.condition_id} is already {condition.status}")
        condition.status = 'MET'
        condition.met_by = met_by
        condition.met_at = timezone.now()
        condition.evidence = evidence or {}
        condition.save(update_fields=['status', 'met_by', 'met_at', 'evidence', 'updated_at'])
        return condition
    
    @staticmethod
    def mark_failed(condition, reason=''):
        if condition.status != 'PENDING':
            raise ValueError(f"Condition {condition.condition_id} is already {condition.status}")
        condition.status = 'FAILED'
        condition.evidence['failure_reason'] = reason
        condition.met_at = timezone.now()
        condition.save(update_fields=['status', 'evidence', 'met_at', 'updated_at'])
        return condition
    
    @staticmethod
    def are_all_required_met(agreement):
        pending = Condition.objects.filter(
            agreement=agreement,
            required=True,
            status='PENDING'
        ).exists()
        return not pending
    
    @staticmethod
    def get_pending_conditions(agreement):
        return Condition.objects.filter(agreement=agreement, required=True, status='PENDING')
    
    @staticmethod
    def check_timeouts():
        from django.utils import timezone
        now = timezone.now()
        timed_out = Condition.objects.filter(
            status='PENDING',
            required=True,
            timeout_at__isnull=False,
            timeout_at__lte=now
        )
        for c in timed_out:
            ConditionService.mark_failed(c, reason='Condition timed out')
            agreement = c.agreement
            if agreement.status == 'HELD':
                from apps.state_machine.services import StateMachine
                try:
                    StateMachine.transition(
                        agreement, 'EXPIRED',
                        triggered_by='condition_timeout',
                        actor_role='system',
                        channel='system',
                        reason=f'Condition "{c.label}" timed out after {c.timeout_hours}h',
                        evidence={'condition_id': c.condition_id, 'timeout_hours': c.timeout_hours}
                    )
                except ValueError:
                    pass
        return list(timed_out)
