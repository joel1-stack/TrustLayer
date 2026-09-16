"""
TrustLayer Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from apps.agreements.models import Case, CaseTimeline, CaseMessage, CaseEvidence
from apps.core.constants import PROBLEM_TYPES, RESOLUTION_TYPES
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def home(request):
    today = timezone.now().date()
    total_cases = Case.objects.count()
    active_cases = Case.objects.exclude(status__in=['RESOLVED', 'CLOSED']).count()
    resolved_today = Case.objects.filter(status='RESOLVED', updated_at__date=today).count()
    return render(request, 'landing.html', {
        'total_cases': total_cases,
        'active_cases': active_cases,
        'resolved_today': resolved_today,
    })


def how_it_works(request):
    return render(request, 'how_it_works.html', {'nav_how': True})


def features(request):
    return render(request, 'features.html', {'nav_features': True})


def about(request):
    return render(request, 'about.html', {'nav_about': True})


def report_page(request):
    return render(request, 'report.html', {'problem_types': PROBLEM_TYPES})


def report_submit(request):
    if request.method == 'POST':
        import secrets, string

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
            priority='HIGH' if amount > 10000 else 'NORMAL',
            status='OPEN',
            status_code_value=10000,
        )

        CaseTimeline.objects.create(
            case=case, from_status='', to_status='OPEN',
            reason='Case created by customer', triggered_by='customer',
        )

        evidence_file = request.FILES.get('evidence')
        if evidence_file:
            CaseEvidence.objects.create(
                case=case,
                evidence_type='screenshot' if evidence_file.content_type.startswith('image/') else 'document',
                filename=evidence_file.name,
                file=evidence_file,
                uploaded_by=customer_name or 'customer',
            )

        return render(request, 'report_success.html', {'case_id': case.case_id})

    return redirect('/report/')


def case_detail(request, case_id):
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    timeline = case.timeline.all().order_by('created_at')
    messages = case.messages.all().order_by('created_at')
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
    return render(request, 'verify.html', {'case': case})


def case_confirm(request, case_id):
    if request.method != 'POST':
        return redirect(f'/case/{case_id}/')
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    from apps.state_machine.services import StateMachine
    confirmed = request.POST.get('confirmed') == 'true'

    if case.status == 'VERIFYING':
        if confirmed:
            StateMachine.transition(case, 'RESOLVED', triggered_by='customer', reason='Customer confirmed resolution')
            case.customer_verified = True
            case.verification_note = request.POST.get('note', '')
            case.save()
        else:
            StateMachine.transition(case, 'REOPENED', triggered_by='customer', reason='Customer says issue persists')
            case.customer_verified = False
            case.save()

    return redirect(f'/case/{case_id}/')


def case_add_message(request, case_id):
    if request.method != 'POST':
        return redirect(f'/case/{case_id}/')
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    CaseMessage.objects.create(
        case=case,
        sender=request.POST.get('sender', request.session.get('customer_name', 'Anonymous')),
        sender_type=request.POST.get('sender_type', 'customer'),
        text=request.POST.get('text', ''),
    )
    return redirect(f'/case/{case_id}/')


def case_evidence_upload(request, case_id):
    if request.method != 'POST':
        return redirect(f'/case/{case_id}/')
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

    return redirect(f'/case/{case_id}/')


def case_track(request):
    case_id = request.GET.get('id', '').strip()
    if case_id:
        return case_detail(request, case_id)
    return render(request, 'track.html')


# --- Agent views ---

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
    cases = Case.objects.all()
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    type_filter = request.GET.get('type', '')
    if status_filter:
        cases = cases.filter(status=status_filter)
    if priority_filter:
        cases = cases.filter(priority=priority_filter)
    if type_filter:
        cases = cases.filter(problem_type=type_filter)
    cases = cases[:50]

    today = timezone.now().date()
    stats = {
        'active_cases': Case.objects.exclude(status__in=['RESOLVED', 'CLOSED']).count(),
        'verifying': Case.objects.filter(status='VERIFYING').count(),
        'escalated': Case.objects.filter(status='ESCALATED').count(),
        'resolved_today': Case.objects.filter(status='RESOLVED', updated_at__date=today).count(),
    }

    return render(request, 'agent_dashboard.html', {
        'cases': cases,
        'agent_name': agent_name,
        'stats': stats,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'type_filter': type_filter,
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
        action = request.POST.get('action', '')

        if action == 'investigate':
            if case.status in ['OPEN', 'EVIDENCE_COLLECTION', 'REOPENED', 'ESCALATED']:
                StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_name, reason='Agent started investigation')

        elif action == 'escalate':
            if case.status == 'INVESTIGATING':
                StateMachine.transition(case, 'ESCALATED', triggered_by=agent_name, reason='Escalated for review')

        elif action == 'resolve':
            resolution_type = request.POST.get('resolution_type', '')
            finding = request.POST.get('finding', '')
            note = request.POST.get('resolution_note', '')
            provider_action = request.POST.get('provider_action', '')

            if case.status in ['OPEN', 'EVIDENCE_COLLECTION', 'REOPENED']:
                StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_name, reason='Agent picked up case')
            if case.status == 'ESCALATED':
                StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_name, reason='Escalation addressed')
            if case.status == 'INVESTIGATING':
                StateMachine.transition(case, 'RESOLUTION_RECORDED', triggered_by=agent_name, reason='Resolution recorded')
                case.resolution_type = resolution_type
                case.resolution_note = note
                case.finding = finding
                case.resolved_by = agent_name
                if provider_action:
                    case.metadata['provider_action'] = provider_action
                case.save()

        elif action == 'message':
            CaseMessage.objects.create(
                case=case,
                sender=agent_name,
                sender_type='agent',
                text=request.POST.get('text', ''),
            )

        elif action == 'add_note':
            note = request.POST.get('note', '')
            if note:
                if case.investigation_notes:
                    case.investigation_notes += f"\n\n[{agent_name}] {note}"
                else:
                    case.investigation_notes = f"[{agent_name}] {note}"
                case.save()

        elif action == 'verify':
            if case.status == 'RESOLUTION_RECORDED':
                StateMachine.transition(case, 'VERIFYING', triggered_by='system', reason='Sent to customer for verification')

        elif action == 'close':
            if case.status == 'RESOLVED':
                StateMachine.transition(case, 'CLOSED', triggered_by='system', reason='Case closed')

        return redirect(f'/agent/case/{case_id}/')

    timeline = case.timeline.all().order_by('created_at')
    messages = case.messages.all().order_by('created_at')
    evidence = case.evidence_items.all().order_by('-created_at')

    return render(request, 'agent_case.html', {
        'case': case,
        'timeline': timeline,
        'messages': messages,
        'evidence': evidence,
        'resolution_types': RESOLUTION_TYPES,
    })


urlpatterns = [
    path('', home, name='home'),
    path('how-it-works/', how_it_works, name='how-it-works'),
    path('features/', features, name='features'),
    path('about/', about, name='about'),
    path('report/', report_page, name='report'),
    path('report/submit/', report_submit, name='report-submit'),
    path('case/<str:case_id>/', case_detail, name='case-detail'),
    path('case/<str:case_id>/verify/', case_verify_page, name='case-verify'),
    path('case/<str:case_id>/confirm/', case_confirm, name='case-confirm'),
    path('case/<str:case_id>/message/', case_add_message, name='case-message'),
    path('case/<str:case_id>/evidence/', case_evidence_upload, name='case-evidence'),
    path('track/', case_track, name='track'),
    path('agent/login/', agent_login, name='agent-login'),
    path('agent/logout/', agent_logout, name='agent-logout'),
    path('agent/', agent_dashboard, name='agent-dashboard'),
    path('agent/case/<str:case_id>/', agent_case, name='agent-case'),
    path('django-admin/', admin.site.urls),
    path('api/v1/', include('apps.api_v1.urls')),
    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('health/', lambda r: JsonResponse({'status': 'ok'})),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
