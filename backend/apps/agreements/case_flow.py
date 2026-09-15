import os
import re
from django.conf import settings
from apps.agreements.models import Case, CaseEvidence, CaseTimeline, CaseMessage
from apps.state_machine.services import StateMachine

PROBLEM_TYPE_MAP = {
    'transaction_dispute': 'TRANSACTION_DISPUTE',
    'TRANSACTION_DISPUTE': 'TRANSACTION_DISPUTE',
    'payment_issue': 'PAYMENT_PROBLEM',
    'PAYMENT_PROBLEM': 'PAYMENT_PROBLEM',
    'account_issue': 'ACCOUNT_PROBLEM',
    'ACCOUNT_PROBLEM': 'ACCOUNT_PROBLEM',
    'other': 'OTHER',
    'OTHER': 'OTHER',
}

TEAM_BY_TYPE = {
    'TRANSACTION_DISPUTE': 'FRAUD_OPERATIONS',
    'PAYMENT_PROBLEM': 'PAYMENTS_OPERATIONS',
    'ACCOUNT_PROBLEM': 'ACCOUNT_SECURITY',
    'OTHER': 'GENERAL_SUPPORT',
}

RESOLUTION_TYPE_MAP = {
    'confirmed_fraud': 'CONFIRMED_FRAUD',
    'CONFIRMED_FRAUD': 'CONFIRMED_FRAUD',
    'legitimate': 'TRANSACTION_LEGITIMATE',
    'TRANSACTION_LEGITIMATE': 'TRANSACTION_LEGITIMATE',
    'customer_error': 'CUSTOMER_ERROR',
    'CUSTOMER_ERROR': 'CUSTOMER_ERROR',
    'unable_to_determine': 'UNABLE_TO_DETERMINE',
    'UNABLE_TO_DETERMINE': 'UNABLE_TO_DETERMINE',
}

RESOLUTION_LABELS = {
    'CONFIRMED_FRAUD': 'Confirmed unauthorized transaction',
    'TRANSACTION_LEGITIMATE': 'Transaction confirmed as legitimate',
    'CUSTOMER_ERROR': 'Customer error',
    'UNABLE_TO_DETERMINE': 'Unable to determine',
}


def normalize_problem_type(raw):
    return PROBLEM_TYPE_MAP.get((raw or '').strip(), 'TRANSACTION_DISPUTE')


def normalize_resolution_type(raw):
    return RESOLUTION_TYPE_MAP.get((raw or '').strip(), '')


def split_contact(contact):
    contact = (contact or '').strip()
    if '@' in contact:
        return contact, ''
    return '', contact


def route_case(problem_type, amount):
    try:
        amount = float(amount or 0)
    except (TypeError, ValueError):
        amount = 0
    team = TEAM_BY_TYPE.get(problem_type, 'GENERAL_SUPPORT')
    if amount > 50000:
        priority = 'CRITICAL'
    elif amount > 10000:
        priority = 'HIGH'
    elif amount > 1000:
        priority = 'NORMAL'
    else:
        priority = 'LOW'
    return team, priority


def record_event(case, to_status, reason, triggered_by='system', from_status=None):
    CaseTimeline.objects.create(
        case=case,
        from_status=from_status if from_status is not None else case.status,
        to_status=to_status,
        reason=reason,
        triggered_by=triggered_by,
    )


def safe_filename(name):
    name = os.path.basename(name or 'evidence.bin')
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    return name[:180] or 'evidence.bin'


def save_evidence_file(case, uploaded, uploaded_by='customer'):
    if not uploaded:
        return None
    dest_dir = os.path.join(settings.MEDIA_ROOT, 'evidence', case.case_id)
    os.makedirs(dest_dir, exist_ok=True)
    filename = safe_filename(uploaded.name)
    path = os.path.join(dest_dir, filename)
    with open(path, 'wb+') as dest:
        for chunk in uploaded.chunks():
            dest.write(chunk)
    url = f'{settings.MEDIA_URL}evidence/{case.case_id}/{filename}'
    return CaseEvidence.objects.create(
        case=case,
        evidence_type='screenshot' if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')) else 'document',
        url=url,
        filename=filename,
        description='Uploaded with case report' if uploaded_by == 'customer' else 'Uploaded by agent',
        uploaded_by=uploaded_by,
    )


def create_case_from_request(data, files=None):
    problem_type = normalize_problem_type(data.get('problem_type'))
    txn_id = (data.get('txn_id') or data.get('transaction_ref') or '').strip()
    amount = data.get('amount') or 0
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0
    currency = data.get('currency') or 'KES'
    description = (data.get('description') or '').strip()
    date_occurred = data.get('date_occurred') or data.get('incident_date') or None
    customer_name = (data.get('customer_name') or '').strip()
    email = (data.get('customer_email') or '').strip()
    phone = (data.get('customer_phone') or '').strip()
    if not email and not phone:
        email, phone = split_contact(data.get('contact'))
    team, priority = route_case(problem_type, amount)

    case = Case.objects.create(
        problem_type=problem_type,
        txn_id=txn_id,
        amount=amount,
        currency=currency,
        description=description,
        date_occurred=date_occurred or None,
        customer_name=customer_name,
        customer_email=email,
        customer_phone=phone,
        assigned_team=team,
        priority=priority,
        status='OPEN',
        status_code_value=10000,
        metadata={
            'routing_reason': f'{problem_type} · amount {currency} {amount}',
        },
    )
    record_event(case, 'OPEN', 'Case created by customer', 'customer', from_status='')
    record_event(case, case.status, f'Routed to {team} ({priority})', 'system')

    uploaded = None
    if files:
        uploaded = files.get('evidence')
    if uploaded:
        save_evidence_file(case, uploaded, 'customer')
        if case.status == 'OPEN':
            StateMachine.transition(case, 'EVIDENCE_COLLECTION', triggered_by='customer', reason='Evidence attached at intake')

    return case


def send_to_verification(case, triggered_by='agent'):
    if case.status == 'RESOLUTION_RECORDED':
        StateMachine.transition(case, 'VERIFYING', triggered_by=triggered_by, reason='Sent to customer for verification')
    return case


def apply_customer_verification(case, confirmed, note='', triggered_by='customer'):
    if case.status == 'RESOLUTION_RECORDED':
        send_to_verification(case, triggered_by='system')
        case.refresh_from_db()
    if case.status != 'VERIFYING':
        return case
    if confirmed:
        StateMachine.transition(case, 'RESOLVED', triggered_by=triggered_by, reason='Customer confirmed resolution')
        case.customer_verified = True
        case.verification_note = note
        case.save(update_fields=['customer_verified', 'verification_note', 'updated_at'])
        if StateMachine.can_transition(case, 'CLOSED'):
            StateMachine.transition(case, 'CLOSED', triggered_by='system', reason='Verified resolution closed the case')
    else:
        StateMachine.transition(case, 'REOPENED', triggered_by=triggered_by, reason=note or 'Customer says the problem remains')
        case.customer_verified = False
        case.save(update_fields=['customer_verified', 'updated_at'])
        case.refresh_from_db()
        if StateMachine.can_transition(case, 'INVESTIGATING'):
            StateMachine.transition(case, 'INVESTIGATING', triggered_by='system', reason='Reopened case returned to investigation')
    return case


def agent_start_investigation(case, agent_id='agent'):
    if case.status == 'REOPENED' and StateMachine.can_transition(case, 'INVESTIGATING'):
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_id, reason='Agent resumed investigation')
    elif case.status in ['OPEN', 'EVIDENCE_COLLECTION'] and StateMachine.can_transition(case, 'INVESTIGATING'):
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_id, reason='Agent started investigation')
    return case


def agent_resolve(case, resolution_type, note, finding='', agent_id='agent', provider_action=''):
    agent_start_investigation(case, agent_id)
    case.refresh_from_db()
    if case.status == 'ESCALATED' and StateMachine.can_transition(case, 'INVESTIGATING'):
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_id, reason='Escalation addressed')
        case.refresh_from_db()
    if case.status != 'INVESTIGATING':
        return case
    StateMachine.transition(case, 'RESOLUTION_RECORDED', triggered_by=agent_id, reason='Resolution recorded')
    case.resolution_type = normalize_resolution_type(resolution_type)
    case.resolution_note = note
    case.finding = finding or RESOLUTION_LABELS.get(case.resolution_type, note)
    case.resolved_by = agent_id
    meta = case.metadata or {}
    if provider_action:
        meta['provider_action'] = provider_action
    case.metadata = meta
    case.save()
    send_to_verification(case, triggered_by=agent_id)
    return case


def agent_escalate(case, agent_id='agent', reason='Escalated by agent'):
    if case.status in ['OPEN', 'EVIDENCE_COLLECTION']:
        agent_start_investigation(case, agent_id)
        case.refresh_from_db()
    if case.status == 'INVESTIGATING' and StateMachine.can_transition(case, 'ESCALATED'):
        StateMachine.transition(case, 'ESCALATED', triggered_by=agent_id, reason=reason)
    return case
