from .models import StateTransition
from apps.agreements.models import STATUS_CODES

VALID_TRANSITIONS = {
    'CREATED': ['CONFIRMED', 'REJECTED', 'CANCELLED'],
    'CONFIRMED': ['SUBMITTED', 'CANCELLED'],
    'SUBMITTED': ['PENDING', 'DECLINED', 'EXPIRED'],
    'PENDING': ['AVAILABLE', 'DECLINED', 'EXPIRED'],
    'AVAILABLE': ['RECONCILING', 'HELD', 'REFUNDED'],
    'RECONCILING': ['HELD', 'REFUNDED'],
    'HELD': ['READY', 'DISPUTED', 'CANCELLED', 'REFUNDED', 'EXPIRED'],
    'DISPUTED': ['READY', 'REFUNDED', 'CANCELLED'],
    'READY': ['SETTLING', 'CANCELLED'],
    'SETTLING': ['SETTLED', 'PARTIALLY_SETTLED', 'FAILED', 'EXPIRED'],
    'PARTIALLY_SETTLED': ['SETTLED', 'RETRYING', 'FAILED_PERMANENT'],
    'FAILED': ['RETRYING', 'FAILED_PERMANENT'],
    'RETRYING': ['SETTLED', 'PARTIALLY_SETTLED', 'FAILED_PERMANENT'],
    'SETTLED': ['REVERSED'],
    'REVERSED': ['REFUNDED'],
    'DECLINED': [],
    'REJECTED': [],
    'CANCELLED': [],
    'EXPIRED': [],
    'REFUNDED': [],
    'FAILED_PERMANENT': [],
}

TERMINAL_STATES = {'DECLINED', 'REJECTED', 'CANCELLED', 'EXPIRED', 'REFUNDED', 'FAILED_PERMANENT'}


class StateMachine:

    @staticmethod
    def transition(agreement, to_status, triggered_by='system', reason='', evidence=None,
                   actor_role='system', channel='system', ip_address=None):
        if to_status not in VALID_TRANSITIONS.get(agreement.status, []):
            raise ValueError(
                f"Cannot transition from {agreement.status} to {to_status}. "
                f"Allowed: {VALID_TRANSITIONS.get(agreement.status, [])}"
            )

        status_code = STATUS_CODES.get(to_status)

        transition = StateTransition.objects.create(
            agreement=agreement,
            from_status=agreement.status,
            to_status=to_status,
            status_code=status_code,
            triggered_by=triggered_by,
            actor_role=actor_role,
            channel=channel,
            ip_address=ip_address,
            reason=reason,
            evidence=evidence or {},
        )

        agreement.status = to_status
        agreement.save(update_fields=['status', 'updated_at'])

        return transition

    @staticmethod
    def can_transition(agreement, to_status):
        return to_status in VALID_TRANSITIONS.get(agreement.status, [])

    @staticmethod
    def get_history(agreement):
        return StateTransition.objects.filter(agreement=agreement)

    @staticmethod
    def get_status_code(state_name):
        return STATUS_CODES.get(state_name)

    @staticmethod
    def is_terminal(state_name):
        return state_name in TERMINAL_STATES
