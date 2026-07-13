from .models import StateTransition
from apps.agreements.models import STATUS_CODES

VALID_TRANSITIONS = {
    'CREATED': ['PENDING_KYC', 'REJECTED', 'CANCELLED'],
    'PENDING_KYC': ['CONFIRMED', 'REJECTED', 'CANCELLED'],
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
                   actor_role='system', channel='system', ip_address=None,
                   actor_id='', provider_ref='', trigger_reason=''):
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
            actor_id=actor_id,
            actor_role=actor_role,
            channel=channel,
            ip_address=ip_address,
            provider_ref=provider_ref,
            trigger_reason=trigger_reason,
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

    @staticmethod
    def get_required_kyc_tier(amount):
        if amount < 50000:
            return 1
        elif amount < 500000:
            return 2
        return 3

    @staticmethod
    def validate_kyc(agreement):
        tier = StateMachine.get_required_kyc_tier(agreement.amount)
        metadata = agreement.metadata or {}
        kyc = metadata.get('kyc', {})
        if tier == 1:
            return bool(kyc.get('phone') or kyc.get('email'))
        elif tier == 2:
            return bool(kyc.get('id_number') and (kyc.get('phone') or kyc.get('email')))
        else:
            return bool(kyc.get('id_number') and kyc.get('id_photo_url') and kyc.get('phone'))
