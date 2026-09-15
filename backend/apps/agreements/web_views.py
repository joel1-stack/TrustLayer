from functools import wraps

from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.agreements.models import Case, CaseMessage
from apps.agreements import case_flow
from apps.state_machine.services import StateMachine


def agent_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.session.get('agent_ok'):
            return view(request, *args, **kwargs)
        nxt = request.get_full_path()
        return redirect(f'/login/?next={nxt}')
    return wrapped


def _agent_id(request):
    return request.session.get('agent_name') or settings.AGENT_USERNAME


def home(request):
    today = timezone.now().date()
    total_cases = Case.objects.count()
    active_cases = Case.objects.exclude(status__in=['RESOLVED', 'CLOSED']).count()
    resolved_today = Case.objects.filter(status__in=['RESOLVED', 'CLOSED'], updated_at__date=today).count()
    return render(request, 'landing.html', {
        'total_cases': total_cases,
        'active_cases': active_cases,
        'resolved_today': resolved_today,
    })


def how_it_works(request):
    return render(request, 'how_it_works.html')


def features_page(request):
    return render(request, 'features.html')


def about_page(request):
    return render(request, 'about.html')


def report_page(request):
    if request.method == 'POST':
        return report_submit(request)
    return render(request, 'report.html')


def report_submit(request):
    if request.method != 'POST':
        return redirect('/report/')
    description = (request.POST.get('description') or '').strip()
    if not description:
        return render(request, 'report.html', {'error': 'Please describe what happened.'})
    case = case_flow.create_case_from_request(request.POST, request.FILES)
    return render(request, 'report_success.html', {'case_id': case.case_id, 'case': case})


def case_detail(request, case_id):
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    timeline = case.timeline.all().order_by('created_at')
    messages = case.messages.exclude(sender_type='note').order_by('created_at')
    evidence = case.evidence_items.all().order_by('-created_at')
    return render(request, 'case_detail.html', {
        'case': case,
        'timeline': timeline,
        'messages': messages,
        'evidence': evidence,
    })


def case_verify_page(request, case_id):
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})
    if request.method == 'POST':
        return case_confirm(request, case_id)
    if case.status == 'RESOLUTION_RECORDED':
        case_flow.send_to_verification(case, triggered_by='customer')
        case.refresh_from_db()
    return render(request, 'verify.html', {'case': case})


def case_confirm(request, case_id):
    if request.method != 'POST':
        return redirect(f'/case/{case_id}/verify/')
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    raw = request.POST.get('confirmed', request.POST.get('verification', ''))
    confirmed = str(raw).lower() in ['true', '1', 'yes', 'resolved']
    note = request.POST.get('note', '')
    case_flow.apply_customer_verification(case, confirmed, note=note)
    return redirect(f'/case/{case_id}/')


@require_POST
def case_add_message(request, case_id):
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})
    text = (request.POST.get('text') or request.POST.get('message') or '').strip()
    if text:
        CaseMessage.objects.create(
            case=case,
            sender=request.POST.get('sender') or case.customer_name or 'Customer',
            sender_type=request.POST.get('sender_type', 'customer'),
            text=text,
        )
        case_flow.record_event(case, case.status, 'Customer sent a message', 'customer')
    return redirect(f'/case/{case_id}/')


def case_track(request):
    case_id = (request.GET.get('id') or '').strip()
    if case_id:
        return case_detail(request, case_id)
    return render(request, 'track.html')


def login_page(request):
    error = ''
    nxt = request.GET.get('next') or request.POST.get('next') or '/admin/'
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        if username == settings.AGENT_USERNAME and password == settings.AGENT_PASSWORD:
            request.session['agent_ok'] = True
            request.session['agent_name'] = username
            return redirect(nxt if nxt.startswith('/') else '/admin/')
        error = 'Invalid agent username or password.'
    return render(request, 'login.html', {'error': error, 'next': nxt})


def logout_page(request):
    request.session.flush()
    return redirect('/')


@agent_required
def admin_dashboard(request):
    cases = Case.objects.all()
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    type_filter = request.GET.get('type', '')
    if status_filter and status_filter != 'all':
        cases = cases.filter(status=status_filter)
    if priority_filter and priority_filter != 'all':
        cases = cases.filter(priority=priority_filter)
    if type_filter and type_filter != 'all':
        cases = cases.filter(problem_type=case_flow.normalize_problem_type(type_filter))
    cases = list(cases[:100])
    today = timezone.now().date()
    all_cases = Case.objects.all()
    stats = {
        'active_cases': all_cases.exclude(status__in=['RESOLVED', 'CLOSED']).count(),
        'resolved_today': all_cases.filter(status__in=['RESOLVED', 'CLOSED'], updated_at__date=today).count(),
        'total': all_cases.count(),
        'verifying': all_cases.filter(status='VERIFYING').count(),
    }
    return render(request, 'agent_dashboard.html', {
        'cases': cases,
        'status_filter': status_filter or 'all',
        'priority_filter': priority_filter or 'all',
        'type_filter': type_filter or 'all',
        'stats': stats,
        'agent_name': _agent_id(request),
    })


@agent_required
def admin_case(request, case_id):
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    if request.method == 'POST':
        action = request.POST.get('action', '')
        agent_id = _agent_id(request)
        if action == 'investigate':
            case_flow.agent_start_investigation(case, agent_id)
        elif action == 'add_note':
            note = (request.POST.get('note') or '').strip()
            if note:
                CaseMessage.objects.create(
                    case=case,
                    sender=agent_id,
                    sender_type='note',
                    text=note,
                )
                notes = case.investigation_notes or ''
                stamp = timezone.now().strftime('%Y-%m-%d %H:%M')
                case.investigation_notes = (notes + f'\n[{stamp} {agent_id}] {note}').strip()
                case.save(update_fields=['investigation_notes', 'updated_at'])
                case_flow.record_event(case, case.status, 'Investigation note added', agent_id)
        elif action == 'resolve':
            note = request.POST.get('resolution_note') or request.POST.get('note') or ''
            finding = request.POST.get('finding', '')
            provider_action = request.POST.get('provider_action') or request.POST.get('internal_note') or ''
            case_flow.agent_resolve(
                case,
                request.POST.get('resolution_type', ''),
                note,
                finding=finding,
                agent_id=agent_id,
                provider_action=provider_action,
            )
        elif action == 'escalate':
            case_flow.agent_escalate(case, agent_id, request.POST.get('note') or 'Escalated by agent')
        elif action == 'verify':
            case_flow.send_to_verification(case, triggered_by=agent_id)
        elif action == 'close':
            if case.status == 'RESOLVED' and StateMachine.can_transition(case, 'CLOSED'):
                StateMachine.transition(case, 'CLOSED', triggered_by=agent_id, reason='Agent closed case')
        elif action == 'message':
            text = (request.POST.get('text') or request.POST.get('message') or '').strip()
            if text:
                CaseMessage.objects.create(
                    case=case,
                    sender=agent_id,
                    sender_type='agent',
                    text=text,
                )
                case_flow.record_event(case, case.status, 'Agent messaged the customer', agent_id)
        return redirect(f'/admin/case/{case_id}/')

    timeline = case.timeline.all().order_by('created_at')
    messages = case.messages.exclude(sender_type='note').order_by('created_at')
    notes = case.messages.filter(sender_type='note').order_by('created_at')
    evidence = case.evidence_items.all().order_by('-created_at')
    return render(request, 'agent_case.html', {
        'case': case,
        'timeline': timeline,
        'messages': messages,
        'notes': notes,
        'evidence': evidence,
        'agent_name': _agent_id(request),
    })


@agent_required
@require_POST
def admin_case_add_message(request, case_id):
    request.POST = request.POST.copy()
    request.POST['action'] = 'message'
    return admin_case(request, case_id)
