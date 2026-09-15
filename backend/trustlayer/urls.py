"""
TrustLayer Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render, redirect
from django.utils import timezone
from apps.agreements.models import Case
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def home(request):
    from apps.core.constants import STATUS_CATEGORIES
    today = timezone.now().date()
    total_cases = Case.objects.count()
    terminal_states = [s for s, c in STATUS_CATEGORIES.items() if c == 'terminal']
    active_cases = Case.objects.exclude(status__in=terminal_states).count()
    resolved_today = Case.objects.filter(status='RESOLVED', updated_at__date=today).count()
    return render(request, 'landing.html', {
        'total_cases': total_cases,
        'active_cases': active_cases,
        'resolved_today': resolved_today,
    })


def report_page(request):
    return render(request, 'report.html')


def report_submit(request):
    if request.method == 'POST':
        from apps.agreements.models import Case, CaseTimeline
        import secrets, string

        txn_id = request.POST.get('txn_id', '')
        amount = request.POST.get('amount', 0)
        description = request.POST.get('description', '')
        customer_name = request.POST.get('customer_name', '')
        customer_email = request.POST.get('customer_email', '')
        customer_phone = request.POST.get('customer_phone', '')
        severity = request.POST.get('severity', 'NORMAL')

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0

        case = Case.objects.create(
            txn_id=txn_id,
            amount=amount,
            description=description,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            severity=severity,
            status='OPEN',
            status_code_value=10000,
        )

        CaseTimeline.objects.create(
            case=case, from_status='', to_status='OPEN',
            reason='Case created', triggered_by='customer',
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


def case_track(request):
    case_id = request.GET.get('id', '').strip()
    if case_id:
        return case_detail(request, case_id)
    return render(request, 'track.html')


def agent_dashboard(request):
    cases = Case.objects.all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        cases = cases.filter(status=status_filter)
    cases = cases[:50]
    return render(request, 'agent_dashboard.html', {'cases': cases, 'status_filter': status_filter})


def agent_case(request, case_id):
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'case_not_found.html', {'case_id': case_id})

    if request.method == 'POST':
        from apps.state_machine.services import StateMachine
        action = request.POST.get('action', '')

        if action == 'investigate':
            StateMachine.transition(case, 'INVESTIGATING', triggered_by='agent', reason='Agent picked up case')
        elif action == 'resolve':
            resolution = request.POST.get('resolution', 'RESOLVED')
            note = request.POST.get('note', '')
            if case.status == 'OPEN':
                StateMachine.transition(case, 'INVESTIGATING', triggered_by='agent', reason='Agent picked up case')
            StateMachine.transition(case, 'RESOLVED', triggered_by='agent', reason=note or 'Case resolved')
            case.resolution = resolution
            case.resolution_note = note
            case.resolved_by = request.POST.get('agent_id', 'agent')
            case.save()
        elif action == 'close':
            StateMachine.transition(case, 'CLOSED', triggered_by='agent', reason='Case closed by agent')

        return redirect(f'/agent/case/{case_id}/')

    timeline = case.timeline.all().order_by('created_at')
    messages = case.messages.all().order_by('created_at')
    evidence = case.evidence_items.all().order_by('-created_at')

    return render(request, 'agent_case.html', {
        'case': case, 'timeline': timeline, 'messages': messages, 'evidence': evidence,
    })


urlpatterns = [
    path('', home),
    path('report/', report_page, name='report'),
    path('report/submit/', report_submit, name='report-submit'),
    path('case/<str:case_id>/', case_detail, name='case-detail'),
    path('track/', case_track, name='track'),
    path('agent/', agent_dashboard, name='agent-dashboard'),
    path('agent/case/<str:case_id>/', agent_case, name='agent-case'),
    path('django-admin/', admin.site.urls),
    path('api/v1/', include('apps.api_v1.urls')),
    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('health/', lambda r: __import__('django.http', fromlist=['JsonResponse']).JsonResponse({'status': 'ok'})),
]
