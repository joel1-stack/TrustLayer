from apps.core.constants import STATUS_CODES, VALID_TRANSITIONS


class StateMachine:

    @staticmethod
    def transition(case, to_status, triggered_by='system', reason='', ip_address=None, actor_role='system'):
        if to_status not in VALID_TRANSITIONS.get(case.status, []):
            raise ValueError(
                f"Cannot transition from {case.status} to {to_status}. "
                f"Allowed: {VALID_TRANSITIONS.get(case.status, [])}"
            )

        from_status = case.status

        from apps.agreements.models import CaseTimeline
        CaseTimeline.objects.create(
            case=case,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            triggered_by=triggered_by,
        )

        case.status = to_status
        case.status_code_value = STATUS_CODES.get(to_status, 10000)
        case.save(update_fields=['status', 'status_code_value', 'updated_at'])

        # Audit engine — log every transition
        try:
            from apps.core.engine_services import log_audit
            log_audit(
                case_id=case.case_id,
                actor=triggered_by,
                action='transition',
                detail=reason,
                from_status=from_status,
                to_status=to_status,
                ip_address=ip_address,
                actor_role=actor_role,
            )
        except Exception:
            pass

        # Notification engine — send notifications on key events
        try:
            from apps.core.engine_services import send_notification
            event_map = {
                'OPEN': 'case_created',
                'VERIFYING': 'verify_request',
                'RESOLVED': 'resolved',
                'REOPENED': 'reopened',
                'CLOSED': 'closed',
            }
            event = event_map.get(to_status)
            if event:
                send_notification(case, event)
        except Exception:
            pass

        return True

    @staticmethod
    def can_transition(case, to_status):
        return to_status in VALID_TRANSITIONS.get(case.status, [])
