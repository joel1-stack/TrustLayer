from .models import StateTransition
from apps.constants import STATUS_CODES, VALID_TRANSITIONS, TERMINAL_STATES
from apps.agreements.models import Agreement


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
        agreement.status_code_value = status_code
        agreement.save(update_fields=['status', 'status_code_value', 'updated_at'])

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

    @staticmethod
    def enforce_held_timeout(max_hold_hours=72):
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=max_hold_hours)
        stuck = Agreement.objects.filter(
            status='HELD',
            updated_at__lte=cutoff
        )
        expired = []
        for agreement in stuck:
            try:
                StateMachine.transition(
                    agreement, 'EXPIRED',
                    triggered_by='system',
                    actor_role='system',
                    channel='system',
                    trigger_reason='held_timeout',
                    reason=f'Auto-expired after {max_hold_hours}h in HELD without conditions being met',
                )
                expired.append(agreement.agreement_id)
            except ValueError:
                pass
        return expired

    @staticmethod
    def enforce_reversal_window(window_hours=24):
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=window_hours)
        stale = Agreement.objects.filter(
            status='SETTLED',
            updated_at__lte=cutoff
        )
        for agreement in stale:
            locked = StateTransition.objects.filter(
                agreement=agreement,
                to_status='REVERSED',
                created_at__gte=cutoff
            ).exists()
            if locked:
                continue
        return len(stale)