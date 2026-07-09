from .models import StateTransition

VALID_TRANSITIONS = {
    'CREATED': ['PAYMENT_PENDING', 'CANCELLED'],
    'PAYMENT_PENDING': ['COLLECTED', 'CANCELLED'],
    'COLLECTED': ['WAITING', 'READY', 'REFUNDED'],
    'WAITING': ['READY', 'REFUNDED'],
    'READY': ['SETTLING'],
    'SETTLING': ['SETTLED', 'REFUNDED', 'WAITING'],
    'SETTLED': [],
    'REFUNDED': [],
    'CANCELLED': [],
}

class StateMachine:

    @staticmethod
    def transition(agreement, to_status, triggered_by='system', reason='', evidence=None):
        if to_status not in VALID_TRANSITIONS.get(agreement.status, []):
            raise ValueError(f"Cannot transition from {agreement.status} to {to_status}")

        transition = StateTransition.objects.create(
            agreement=agreement,
            from_status=agreement.status,
            to_status=to_status,
            triggered_by=triggered_by,
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