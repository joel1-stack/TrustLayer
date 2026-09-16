"""
TrustLayer v1 — Root URL Configuration
14 pages. 5 engines. One loop.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.agreements.models import Case, CaseTimeline, CaseMessage, CaseEvidence
from apps.core.constants import PROBLEM_TYPES, RESOLUTION_TYPES


# ══════════════════════════════════════════════════════════════════════════════
# ZONE A — Customer Portal
# ══════════════════════════════════════════════════════════════════════════════

def home(request):
    """A1 — Redirect to report page."""
    return redirect('/report/')


def how_it_works(request):
    return render(request, 'how_it_works.html', {'nav_how': True})


def features(request):
    return render(request, 'features.html', {'nav_features': True})


def about(request):
    return render(request, 'about.html', {'nav_about': True})


def report_page(request):
    """A1 — Report a Problem."""
    return render(request, 'report.html', {'problem_types': PROBLEM_TYPES})


def report_submit(request):
    """A1 — Submit form → A2 case created."""
    if request.method == 'POST':
        problem_type = request.POST.get('problem_type', 'TRANSACTION_DISPUTE')
        txn_id = request.POST.get('txn_id', '')
        amount = request.POST.get('amount', 0)
        currency = request.POST.get('currency', 'KES')
        description = request.POST.get('description', '')
        date_occurred = request.POST.get('date_occurred') or None
        customer_name = request.POST.get('customer_name', '')
        customer_email = request.POST.get('customer_email', '')
        customer_phone = request.POST.get('customer_phone', '')

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0

        from apps.core.constants import TEAM_BY_PROBLEM
        team = TEAM_BY_PROBLEM.get(problem_type, 'GENERAL_SUPPORT')
        priority = 'HIGH' if amount > 10000 else 'NORMAL'

        case = Case.objects.create(
            problem_type=problem_type,
            txn_id=txn_id,
            amount=amount,
            currency=currency,
            description=description,
            date_occurred=date_occurred,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            priority=priority,
            assigned_team=team,
            status='OPEN',
            status_code_value=10000,
        )

        CaseTimeline.objects.create(
            case=case, from_status='', to_status='OPEN',
            reason='Case created by customer', triggered_by='customer',
        )

        # Audit
        try:
            from apps.core.engine_services import log_audit
            log_audit(case.case_id, 'customer', 'case_created', 'Case submitted via web form', '', 'OPEN')
        except Exception:
            pass

        # Notification
        try:
            from apps.core.engine_services import send_notification
            send_notification(case, 'case_created')
        except Exception:
            pass

        evidence_file = request.FILES.get('evidence')
        if evidence_file:
            CaseEvidence.objects.create(
                case=case,
                evidence_type='screenshot' if evidence_file.content_type.startswith('image/') else 'document',
                filename=evidence_file.name,
                file=evidence_file,
                uploaded_by=customer_name or 'customer',
            )

        return render(request, 'case_created.html', {'case': case})

    return redirect('/report/')


def case_created_page(request, case_id):
    """A2 — Case Created Confirmation."""
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})
    return render(request, 'case_created.html', {'case': case})


def case_track(request, case_id):
    """A3 — Case Tracking."""
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    timeline = case.timeline.all().order_by('created_at')
    messages = case.messages.all().order_by('created_at')
    evidence = case.evidence_items.all().order_by('-created_at')

    return render(request, 'track_case.html', {
        'case': case,
        'timeline': timeline,
        'messages': messages,
        'evidence': evidence,
    })


def case_track_lookup(request):
    """Track page — lookup by case ID."""
    case_id = request.GET.get('id', '').strip()
    if case_id:
        return case_track(request, case_id)
    return render(request, 'track.html')


def case_add_info_page(request, case_id):
    """A4 — Upload / Add Information."""
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    from apps.core.engine_services import check_evidence_completeness
    is_complete, checklist = check_evidence_completeness(case)
    missing = [v['label'] for v in checklist.values() if not v['present'] and v['required']]

    return render(request, 'add_info.html', {
        'case': case,
        'missing_items': missing,
        'completeness': checklist,
    })


def case_add_info_submit(request, case_id):
    """A4 — Submit additional information."""
    if request.method != 'POST':
        return redirect(f'/case/{case_id}/add-info/')
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    text = request.POST.get('text', '')
    evidence_file = request.FILES.get('evidence')

    if text:
        CaseMessage.objects.create(
            case=case,
            sender=case.customer_name or 'Customer',
            sender_type='customer',
            text=text,
        )

    if evidence_file:
        CaseEvidence.objects.create(
            case=case,
            evidence_type='screenshot' if evidence_file.content_type.startswith('image/') else 'document',
            filename=evidence_file.name,
            file=evidence_file,
            uploaded_by=case.customer_name or 'customer',
        )

    try:
        from apps.core.engine_services import send_notification
        send_notification(case, 'evidence_uploaded')
    except Exception:
        pass

    return redirect(f'/case/{case_id}/track/')


def case_verify_page(request, case_id):
    """A5 — Resolution Check."""
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})
    return render(request, 'verify.html', {'case': case})


def case_confirm(request, case_id):
    """A5 — Customer confirms or rejects."""
    if request.method != 'POST':
        return redirect(f'/case/{case_id}/track/')
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    from apps.state_machine.services import StateMachine
    confirmed = request.POST.get('confirmed') == 'true'

    if case.status == 'VERIFYING':
        if confirmed:
            StateMachine.transition(case, 'RESOLVED', triggered_by='customer', reason='Customer confirmed resolution', actor_role='customer')
            case.customer_verified = True
            case.verification_note = request.POST.get('note', '')
            case.save()
        else:
            StateMachine.transition(case, 'REOPENED', triggered_by='customer', reason='Customer says issue persists', actor_role='customer')
            case.customer_verified = False
            case.save()

    if confirmed:
        return redirect(f'/case/{case_id}/closed/')
    return redirect(f'/case/{case_id}/track/')


def case_closed_page(request, case_id):
    """A6 — Case Closed."""
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})
    return render(request, 'case_closed.html', {'case': case})


def case_add_message(request, case_id):
    if request.method != 'POST':
        return redirect(f'/case/{case_id}/track/')
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    CaseMessage.objects.create(
        case=case,
        sender=request.POST.get('sender', case.customer_name or 'Anonymous'),
        sender_type=request.POST.get('sender_type', 'customer'),
        text=request.POST.get('text', ''),
    )
    return redirect(f'/case/{case_id}/track/')


def case_evidence_upload(request, case_id):
    if request.method != 'POST':
        return redirect(f'/case/{case_id}/track/')
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    evidence_file = request.FILES.get('evidence')
    if evidence_file:
        CaseEvidence.objects.create(
            case=case,
            evidence_type='screenshot' if evidence_file.content_type.startswith('image/') else 'document',
            filename=evidence_file.name,
            file=evidence_file,
            uploaded_by=case.customer_name or 'customer',
        )
        if case.status == 'OPEN':
            from apps.state_machine.services import StateMachine
            StateMachine.transition(case, 'EVIDENCE_COLLECTION', triggered_by='customer', reason='Evidence uploaded')

    return redirect(f'/case/{case_id}/track/')


# ══════════════════════════════════════════════════════════════════════════════
# ZONE B — Agent Workspace
# ══════════════════════════════════════════════════════════════════════════════

def agent_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        if username == 'joelkaunda15' and password == 'wherby':
            request.session['is_agent'] = True
            request.session['agent_name'] = username
            return redirect('/agent/')
        return render(request, 'agent_login.html', {'error': 'Invalid credentials'})
    return render(request, 'agent_login.html')


def agent_logout(request):
    request.session.flush()
    return redirect('/')


def agent_dashboard(request):
    if not request.session.get('is_agent'):
        return redirect('/agent/login/')

    agent_name = request.session.get('agent_name', 'agent')
    tab = request.GET.get('tab', '')
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')

    cases = Case.objects.all()

    # Tab filtering
    if tab == 'my':
        cases = cases.filter(assigned_team__icontains=agent_name[:8])
    elif tab == 'unassigned':
        cases = cases.filter(status='OPEN')
    elif tab == 'escalated':
        cases = cases.filter(status='ESCALATED')
    elif tab == 'awaiting':
        cases = cases.filter(status='VERIFYING')

    if status_filter:
        cases = cases.filter(status=status_filter)
    if priority_filter:
        cases = cases.filter(priority=priority_filter)

    cases = list(cases[:50])

    # Add SLA + age to each case
    from apps.core.engine_services import get_sla_status
    from django.utils import timezone as tz
    now = tz.now()
    for c in cases:
        sla_status, sla_percent, sla_time = get_sla_status(c)
        c.sla_status = sla_status
        c.sla_time = sla_time
        age_delta = now - c.created_at
        days = age_delta.days
        hours = age_delta.seconds // 3600
        c.age = f"{days}d {hours}h" if days > 0 else f"{hours}h"

    today = now.date()
    stats = {
        'active_cases': Case.objects.exclude(status__in=['RESOLVED', 'CLOSED']).count(),
        'verifying': Case.objects.filter(status='VERIFYING').count(),
        'escalated': Case.objects.filter(status='ESCALATED').count(),
        'resolved_today': Case.objects.filter(status='RESOLVED', updated_at__date=today).count(),
        'sla_warning': sum(1 for c in Case.objects.exclude(status__in=['RESOLVED', 'CLOSED']) if get_sla_status(c)[0] == 'warning'),
        'sla_breached': sum(1 for c in Case.objects.exclude(status__in=['RESOLVED', 'CLOSED']) if get_sla_status(c)[0] == 'breached'),
    }

    return render(request, 'agent_dashboard.html', {
        'cases': cases,
        'agent_name': agent_name,
        'stats': stats,
        'tab': tab,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
    })


def agent_case(request, case_id):
    if not request.session.get('is_agent'):
        return redirect('/agent/login/')

    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    agent_name = request.session.get('agent_name', 'agent')

    if request.method == 'POST':
        from apps.state_machine.services import StateMachine
        from apps.core.engine_services import check_evidence_completeness, log_audit, send_notification
        action = request.POST.get('action', '')

        if action == 'investigate':
            if case.status in ['OPEN', 'EVIDENCE_COLLECTION', 'REOPENED', 'ESCALATED']:
                StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_name, reason='Agent started investigation', actor_role='agent')

        elif action == 'escalate':
            if case.status in ['INVESTIGATING', 'OPEN', 'EVIDENCE_COLLECTION']:
                StateMachine.transition(case, 'ESCALATED', triggered_by=agent_name, reason='Escalated for review', actor_role='agent')

        elif action == 'request_info':
            try:
                send_notification(case, 'info_requested')
                log_audit(case.case_id, agent_name, 'info_requested', 'Agent requested more information from customer', case.status, case.status, actor_role='agent')
            except Exception:
                pass

        elif action == 'resolve':
            resolution_type = request.POST.get('resolution_type', '')
            finding = request.POST.get('finding', '')
            note = request.POST.get('resolution_note', '')

            if case.status in ['OPEN', 'EVIDENCE_COLLECTION', 'REOPENED']:
                StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_name, reason='Agent picked up case', actor_role='agent')
            if case.status == 'ESCALATED':
                StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_name, reason='Escalation addressed', actor_role='agent')
            if case.status == 'INVESTIGATING':
                StateMachine.transition(case, 'RESOLUTION_RECORDED', triggered_by=agent_name, reason='Resolution recorded', actor_role='agent')
                case.resolution_type = resolution_type
                case.resolution_note = note
                case.finding = finding
                case.resolved_by = agent_name
                case.save()

        elif action == 'message':
            CaseMessage.objects.create(
                case=case,
                sender=agent_name,
                sender_type='agent',
                text=request.POST.get('text', ''),
            )
            log_audit(case.case_id, agent_name, 'message', 'Agent sent message to customer', actor_role='agent')

        elif action == 'add_note':
            note = request.POST.get('note', '')
            if note:
                if case.investigation_notes:
                    case.investigation_notes += f"\n\n[{agent_name}] {note}"
                else:
                    case.investigation_notes = f"[{agent_name}] {note}"
                case.save()
                log_audit(case.case_id, agent_name, 'note_added', 'Agent added internal note', actor_role='agent')

        elif action == 'verify':
            if case.status == 'RESOLUTION_RECORDED':
                StateMachine.transition(case, 'VERIFYING', triggered_by='system', reason='Sent to customer for verification')

        elif action == 'close':
            if case.status == 'RESOLVED':
                StateMachine.transition(case, 'CLOSED', triggered_by='system', reason='Case closed')

        return redirect(f'/agent/case/{case_id}/')

    from apps.core.engine_services import check_evidence_completeness, get_sla_status
    is_complete, completeness = check_evidence_completeness(case)
    sla_status, sla_percent, sla_time = get_sla_status(case)

    from django.utils import timezone as tz
    age_delta = tz.now() - case.created_at
    days = age_delta.days
    hours = age_delta.seconds // 3600
    age = f"{days}d {hours}h" if days > 0 else f"{hours}h"

    case.sla_status = sla_status
    case.sla_time = sla_time
    case.age = age

    timeline = case.timeline.all().order_by('created_at')
    messages = case.messages.all().order_by('created_at')
    evidence = case.evidence_items.all().order_by('-created_at')

    return render(request, 'agent_case.html', {
        'case': case,
        'timeline': timeline,
        'messages': messages,
        'evidence': evidence,
        'resolution_types': RESOLUTION_TYPES,
        'completeness': completeness,
    })


# ══════════════════════════════════════════════════════════════════════════════
# ZONE C — Admin & Compliance
# ══════════════════════════════════════════════════════════════════════════════

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        if username == 'joelkaunda15' and password == 'wherby':
            request.session['is_agent'] = True
            request.session['is_admin'] = True
            request.session['agent_name'] = username
            return redirect('/admin-panel/')
        return render(request, 'agent_login.html', {'error': 'Invalid credentials'})
    return render(request, 'agent_login.html')


def admin_dashboard(request):
    if not request.session.get('is_admin'):
        return redirect('/admin/login/')

    from apps.core.engine_services import get_sla_status
    from django.db.models import Count, Q
    from django.utils import timezone as tz

    all_cases = Case.objects.all()
    today = tz.now().date()

    total = all_cases.count()
    open_count = all_cases.filter(status='OPEN').count()
    investigating = all_cases.filter(status='INVESTIGATING').count()
    escalated = all_cases.filter(status='ESCALATED').count()
    verifying = all_cases.filter(status='VERIFYING').count()
    resolved_today = all_cases.filter(status='RESOLVED', updated_at__date=today).count()
    resolved_total = all_cases.filter(status__in=['RESOLVED', 'CLOSED']).count()
    reopened_total = all_cases.filter(status='REOPENED').count()

    sla_warning = 0
    sla_breached = 0
    for c in all_cases.exclude(status__in=['RESOLVED', 'CLOSED']):
        s, _, _ = get_sla_status(c)
        if s == 'warning':
            sla_warning += 1
        elif s == 'breached':
            sla_breached += 1

    verification_rate = round((resolved_total / total * 100) if total > 0 else 0, 1)
    reopen_rate = round((reopened_total / total * 100) if total > 0 else 0, 1)

    # Median resolution time (simplified)
    median_resolution_hours = '—'

    # Team workload
    teams = list(
        all_cases.exclude(status__in=['RESOLVED', 'CLOSED'])
        .values('assigned_team')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    team_list = [{'name': t['assigned_team'], 'count': t['count']} for t in teams]

    recent = all_cases[:10]

    stats = {
        'total': total,
        'open': open_count,
        'investigating': investigating,
        'escalated': escalated,
        'verifying': verifying,
        'awaiting_customer': verifying,
        'resolved_today': resolved_today,
        'sla_warning': sla_warning,
        'sla_breached': sla_breached,
        'verification_rate': verification_rate,
        'reopen_rate': reopen_rate,
        'median_resolution_hours': median_resolution_hours,
    }

    return render(request, 'admin_dashboard.html', {
        'stats': stats,
        'teams': team_list,
        'recent_cases': recent,
    })


def admin_cases(request):
    if not request.session.get('is_admin'):
        return redirect('/admin/login/')

    cases = Case.objects.all()
    total = cases.count()
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    type_filter = request.GET.get('type', '')

    if status_filter:
        cases = cases.filter(status=status_filter)
    if priority_filter:
        cases = cases.filter(priority=priority_filter)
    if type_filter:
        cases = cases.filter(problem_type=type_filter)

    return render(request, 'admin_cases.html', {
        'cases': cases[:100],
        'total': total,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'type_filter': type_filter,
    })


def admin_routing(request):
    if not request.session.get('is_admin'):
        return redirect('/admin/login/')
    from apps.core.engines import SLARule
    rules = SLARule.objects.all()
    return render(request, 'admin_routing.html', {'rules': rules})


def admin_users(request):
    if not request.session.get('is_admin'):
        return redirect('/admin/login/')
    teams = [
        {'name': 'FRAUD_OPERATIONS', 'case_type': 'TRANSACTION_DISPUTE', 'member_count': '—'},
        {'name': 'PAYMENTS_OPERATIONS', 'case_type': 'PAYMENT_PROBLEM', 'member_count': '—'},
        {'name': 'ACCOUNT_SECURITY', 'case_type': 'ACCOUNT_PROBLEM', 'member_count': '—'},
        {'name': 'GENERAL_SUPPORT', 'case_type': 'OTHER', 'member_count': '—'},
    ]
    return render(request, 'admin_users.html', {'teams': teams})


def admin_audit(request):
    if not request.session.get('is_admin'):
        return redirect('/admin/login/')
    from apps.core.engines import AuditLog
    logs = AuditLog.objects.all()
    query = request.GET.get('q', '')
    action_filter = request.GET.get('action', '')

    if query:
        logs = logs.filter(case_id__icontains=query) | logs.filter(actor__icontains=query) | logs.filter(action__icontains=query)
    if action_filter:
        logs = logs.filter(action=action_filter)

    total = logs.count()
    return render(request, 'admin_audit.html', {
        'logs': logs[:200],
        'total': total,
        'query': query,
        'action_filter': action_filter,
    })


def admin_notifications(request):
    if not request.session.get('is_admin'):
        return redirect('/admin/login/')
    from apps.core.engine_services import NOTIFICATION_TEMPLATES
    templates = []
    for event, channels in NOTIFICATION_TEMPLATES.items():
        for channel, body in channels.items():
            templates.append({'event': event, 'channel': channel, 'body': body})
    return render(request, 'admin_notifications.html', {'templates': templates})


# ══════════════════════════════════════════════════════════════════════════════
# Infrastructure
# ══════════════════════════════════════════════════════════════════════════════

@extend_schema(
    summary='Health check',
    description='Returns service health status. Use this to verify the API is running.',
    responses={200: OpenApiResponse(description='Service is healthy')},
    tags=['System'],
)
def health_check(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db = 'ok'
    except Exception:
        db = 'error'
    return JsonResponse({'status': 'ok', 'database': db})


# ══════════════════════════════════════════════════════════════════════════════
# URL patterns
# ══════════════════════════════════════════════════════════════════════════════

urlpatterns = [
    # A1 — Report
    path('', home, name='home'),
    path('how-it-works/', how_it_works, name='how-it-works'),
    path('features/', features, name='features'),
    path('about/', about, name='about'),
    path('report/', report_page, name='report'),
    path('report/submit/', report_submit, name='report-submit'),

    # A2 — Case Created
    path('case/<str:case_id>/created/', case_created_page, name='case-created'),

    # A3 — Track
    path('track/', case_track_lookup, name='track-lookup'),
    path('case/<str:case_id>/track/', case_track, name='case-track'),

    # A4 — Add Info
    path('case/<str:case_id>/add-info/', case_add_info_page, name='case-add-info'),
    path('case/<str:case_id>/add-info/submit/', case_add_info_submit, name='case-add-info-submit'),

    # A5 — Verify
    path('case/<str:case_id>/verify/', case_verify_page, name='case-verify'),
    path('case/<str:case_id>/confirm/', case_confirm, name='case-confirm'),

    # A6 — Closed
    path('case/<str:case_id>/closed/', case_closed_page, name='case-closed'),

    # Case details + actions
    path('case/<str:case_id>/', case_track, name='case-detail'),
    path('case/<str:case_id>/message/', case_add_message, name='case-message'),
    path('case/<str:case_id>/evidence/', case_evidence_upload, name='case-evidence'),

    # B1 — Agent Login
    path('agent/login/', agent_login, name='agent-login'),
    path('agent/logout/', agent_logout, name='agent-logout'),

    # B2 — Agent Queue
    path('agent/', agent_dashboard, name='agent-dashboard'),

    # B3 — Agent Case Workspace
    path('agent/case/<str:case_id>/', agent_case, name='agent-case'),

    # C1 — Admin Login
    path('admin/login/', admin_login, name='admin-login'),

    # C1 — Admin Dashboard
    path('admin-panel/', admin_dashboard, name='admin-dashboard'),

    # C2 — Case Management
    path('admin-panel/cases/', admin_cases, name='admin-cases'),

    # C3 — Routing & SLA
    path('admin-panel/routing/', admin_routing, name='admin-routing'),

    # C4 — Users & Teams
    path('admin-panel/users/', admin_users, name='admin-users'),

    # C5 — Notification Templates
    path('admin-panel/notifications/', admin_notifications, name='admin-notifications'),

    # C6 — Audit Log
    path('admin-panel/audit/', admin_audit, name='admin-audit'),

    # Infrastructure
    path('django-admin/', admin.site.urls),
    path('api/v1/', include('apps.api_v1.urls')),
    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('health/', health_check),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
