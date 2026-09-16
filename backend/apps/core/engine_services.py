"""
TrustLayer v1 — Engine services.
Deterministic engines: evidence, routing, SLA, notification, audit.
"""
from django.utils import timezone
from datetime import timedelta
from apps.core.constants import TEAM_BY_PROBLEM, STATUS_CODES


# ─── Evidence Completeness Engine ─────────────────────────────────────────────

EVIDENCE_CHECKLIST = {
    'TRANSACTION_DISPUTE': {
        'required': ['txn_id', 'amount', 'date_occurred', 'description'],
        'optional': ['screenshot', 'document'],
    },
    'PAYMENT_PROBLEM': {
        'required': ['txn_id', 'amount', 'description'],
        'optional': ['screenshot', 'document'],
    },
    'ACCOUNT_PROBLEM': {
        'required': ['description'],
        'optional': ['screenshot', 'document'],
    },
    'OTHER': {
        'required': ['description'],
        'optional': ['screenshot', 'document'],
    },
}


def check_evidence_completeness(case):
    """
    Returns (is_complete, checklist_dict).
    checklist_dict = {field: {'label': str, 'present': bool, 'required': bool}}
    """
    rules = EVIDENCE_CHECKLIST.get(case.problem_type, EVIDENCE_CHECKLIST['OTHER'])
    checklist = {}

    for field in rules['required']:
        val = getattr(case, field, None)
        if field == 'amount':
            present = bool(val and float(val) > 0)
        elif field == 'date_occurred':
            present = bool(val)
        else:
            present = bool(val and str(val).strip())
        checklist[field] = {
            'label': field.replace('_', ' ').title(),
            'present': present,
            'required': True,
        }

    # Check evidence files
    evidence_count = case.evidence_items.count()
    has_evidence = evidence_count > 0
    checklist['evidence_file'] = {
        'label': 'Screenshot or document',
        'present': has_evidence,
        'required': False,
    }

    required_met = all(v['present'] for v in checklist.values() if v['required'])
    return required_met, checklist


# ─── Routing Engine ───────────────────────────────────────────────────────────

def route_case(case):
    """
    Assigns team + priority based on case type + amount.
    Returns (team, priority, rule_description).
    """
    team = TEAM_BY_PROBLEM.get(case.problem_type, 'GENERAL_SUPPORT')
    amount = float(case.amount) if case.amount else 0

    if amount > 100000:
        priority = 'CRITICAL'
    elif amount > 10000:
        priority = 'HIGH'
    else:
        priority = 'NORMAL'

    rule = f"{case.problem_type} → {team}"
    return team, priority, rule


# ─── SLA Engine ───────────────────────────────────────────────────────────────

def get_sla_deadline(case):
    """Returns (deadline_datetime, first_response_deadline) or (None, None)."""
    from apps.core.engines import SLARule
    try:
        rule = SLARule.objects.get(case_type=case.problem_type)
    except SLARule.DoesNotExist:
        rule = None

    if not rule:
        # Default: 24h first response, 72h resolution
        first_response = case.created_at + timedelta(hours=24)
        resolution = case.created_at + timedelta(hours=72)
    else:
        first_response = case.created_at + timedelta(hours=rule.first_response_hours)
        resolution = case.created_at + timedelta(hours=rule.resolution_hours)

    return resolution, first_response


def get_sla_status(case):
    """
    Returns (status, percent_used, time_remaining_str).
    status: 'ok' | 'warning' | 'breached' | 'resolved'
    """
    if case.status in ('RESOLVED', 'CLOSED'):
        return 'resolved', 0, 'Done'

    deadline, first_response = get_sla_deadline(case)
    now = timezone.now()

    if not deadline:
        return 'ok', 0, '—'

    total_seconds = (deadline - case.created_at).total_seconds()
    elapsed_seconds = (now - case.created_at).total_seconds()

    if total_seconds <= 0:
        return 'breached', 100, 'Overdue'

    percent = int((elapsed_seconds / total_seconds) * 100)
    remaining = deadline - now

    if remaining.total_seconds() <= 0:
        return 'breached', 100, 'Overdue'

    hours = int(remaining.total_seconds() // 3600)
    mins = int((remaining.total_seconds() % 3600) // 60)

    if hours > 24:
        days = hours // 24
        hours = hours % 24
        time_str = f"{days}d {hours}h"
    else:
        time_str = f"{hours}h {mins}m"

    from apps.core.engines import SLARule
    try:
        rule = SLARule.objects.get(case_type=case.problem_type)
        warning_at = rule.warning_at_percent
    except SLARule.DoesNotExist:
        warning_at = 80

    if percent >= 100:
        return 'breached', percent, time_str
    elif percent >= warning_at:
        return 'warning', percent, time_str
    else:
        return 'ok', percent, time_str


# ─── Notification Engine ──────────────────────────────────────────────────────

NOTIFICATION_TEMPLATES = {
    'case_created': {
        'sms': 'Your case {case_id} has been received. We will review it shortly.',
        'email': 'Your case {case_id} has been received.\n\nWe will review it and get back to you within 24 hours.\n\nTrack your case: {track_url}',
        'in_app': 'Case {case_id} created successfully.',
    },
    'evidence_uploaded': {
        'in_app': 'Evidence uploaded to case {case_id}.',
    },
    'info_requested': {
        'sms': 'We need more information for case {case_id}. Please check your case page.',
        'email': 'We need more information for case {case_id}.\n\nPlease visit: {case_url}',
        'in_app': 'Information requested for case {case_id}.',
    },
    'resolved': {
        'sms': 'A resolution has been recorded for case {case_id}. Please verify.',
        'email': 'A resolution has been recorded for case {case_id}.\n\nPlease verify: {verify_url}',
        'in_app': 'Resolution recorded for case {case_id}. Please verify.',
    },
    'verify_request': {
        'sms': 'Please verify the resolution for case {case_id}.',
        'in_app': 'Your confirmation is needed for case {case_id}.',
    },
    'reopened': {
        'sms': 'Case {case_id} has been reopened and is back under investigation.',
        'in_app': 'Case {case_id} has been reopened.',
    },
    'closed': {
        'sms': 'Case {case_id} is now closed. Thank you.',
        'email': 'Case {case_id} is now closed.\n\nThank you for using TrustLayer.',
        'in_app': 'Case {case_id} has been closed.',
    },
}


def send_notification(case, event, base_url='https://miranda-stockish-spacially.ngrok-free.dev'):
    """Create notification records for an event. Returns list of Notification objects."""
    from apps.core.engines import Notification

    templates = NOTIFICATION_TEMPLATES.get(event, {})
    notifications = []

    track_url = f"{base_url}/case/{case.case_id}/track/"
    case_url = f"{base_url}/case/{case.case_id}/"
    verify_url = f"{base_url}/case/{case.case_id}/verify/"

    context = {
        'case_id': case.case_id,
        'track_url': track_url,
        'case_url': case_url,
        'verify_url': verify_url,
    }

    # Determine recipients
    recipients = []
    if case.customer_phone:
        recipients.append(('sms', case.customer_phone))
    if case.customer_email:
        recipients.append(('email', case.customer_email))

    # Always add in-app
    recipients.append(('in_app', case.customer_name or 'customer'))

    for channel, recipient in recipients:
        template = templates.get(channel, '')
        if not template:
            continue
        body = template.format(**context)
        n = Notification.objects.create(
            case_id=case.case_id,
            event=event,
            channel=channel,
            recipient=recipient,
            body=body,
            sent=(channel == 'in_app'),
            sent_at=timezone.now() if channel == 'in_app' else None,
        )
        notifications.append(n)

    return notifications


# ─── Audit Engine ─────────────────────────────────────────────────────────────

def log_audit(case_id, actor, action, detail='', from_status='', to_status='', ip_address=None, actor_role='system'):
    """Append an audit log entry. Cannot be edited or deleted."""
    from apps.core.engines import AuditLog
    return AuditLog.objects.create(
        case_id=case_id,
        actor=actor,
        actor_role=actor_role,
        action=action,
        detail=detail,
        from_status=from_status,
        to_status=to_status,
        ip_address=ip_address,
    )
