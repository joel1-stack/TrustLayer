from apps.core.constants import STATUS_CODES, VALID_TRANSITIONS


class StateMachine:

    @staticmethod
    def transition(case, to_status, triggered_by='system', reason=''):
        if to_status not in VALID_TRANSITIONS.get(case.status, []):
            raise ValueError(
                f"Cannot transition from {case.status} to {to_status}. "
                f"Allowed: {VALID_TRANSITIONS.get(case.status, [])}"
            )

        from apps.agreements.models import CaseTimeline
        CaseTimeline.objects.create(
            case=case,
            from_status=case.status,
            to_status=to_status,
            reason=reason,
            triggered_by=triggered_by,
        )

        case.status = to_status
        case.status_code_value = STATUS_CODES.get(to_status, 10000)
        case.save(update_fields=['status', 'status_code_value', 'updated_at'])

        return True

    @staticmethod
    def can_transition(case, to_status):
        return to_status in VALID_TRANSITIONS.get(case.status, [])
