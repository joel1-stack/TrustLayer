"""
TrustLayer Root URL Configuration — V1 API + Swagger + Admin + Internal.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render, redirect
from django.db.models import Count
from django.utils import timezone
from apps.admin_dashboard.views.infrastructure import health_json, containers_json
from apps.admin_dashboard.views.engines import engine_test, provider_test
from apps.core.marketplace import manifest_view
from apps.agreements.models import Case as Agreement
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.admin_dashboard.views.docs import docs_view


def home(request):
    today = timezone.now().date()
    total_cases = Agreement.objects.count()

    # Operational stats — no financial data on the public landing page
    from apps.core.constants import STATUS_CATEGORIES
    terminal_states = [s for s, c in STATUS_CATEGORIES.items() if c == 'terminal']
    active_cases = Agreement.objects.exclude(status__in=terminal_states).count()

    resolved_today = Agreement.objects.filter(
        status__in=['RESOLVED', 'SETTLED'],
        updated_at__date=today
    ).count()

    total_closed_today = Agreement.objects.filter(
        status__in=terminal_states,
        updated_at__date=today
    ).count()
    if total_closed_today > 0:
        rate = round((resolved_today / total_closed_today) * 100)
        auto_resolved_rate = f"{rate}%"
    else:
        auto_resolved_rate = "—"

    return render(request, 'landing.html', {
        'total_cases':        total_cases,
        'active_cases':       active_cases,
        'resolved_today':     resolved_today,
        'auto_resolved_rate': auto_resolved_rate,
    })


def docs_redirect(request):
    return redirect('/admin/docs/')


def consumer_signin(request):
    return render(request, 'consumer_signin.html')


def consumer_auth_email(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            request.session['consumer_email'] = email
            request.session['consumer_name'] = email.split('@')[0].title()
            return redirect('/report/verify/')
    return redirect('/report/')


def consumer_auth_google(request):
    request.session['consumer_email'] = 'user@gmail.com'
    request.session['consumer_name'] = 'Google User'
    return redirect('/report/verify/')


def consumer_auth_linkedin(request):
    request.session['consumer_email'] = 'user@linkedin.com'
    request.session['consumer_name'] = 'LinkedIn User'
    return redirect('/report/verify/')


def consumer_verify_phone(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        if phone:
            request.session['consumer_phone'] = phone
            return redirect('/portal/consumer/')
    return redirect('/report/verify/')


def consumer_verify(request):
    return render(request, 'consumer_verify.html', {
        'user_name': request.session.get('consumer_name', 'there'),
    })


def consumer_home(request):
    from apps.agreements.models import Case
    cases = Case.objects.order_by('-updated_at')[:10]
    case_list = []
    for c in cases:
        status = c.status or 'SUBMITTED'
        status_map = {
            'SETTLED': ('resolved', 'Resolved', '✅'),
            'CANCELLED': ('resolved', 'Resolved', '✅'),
            'REFUNDED': ('resolved', 'Resolved', '✅'),
            'FAILED': ('resolved', 'Resolved', '✅'),
            'DISPUTED': ('investigating', 'Investigating', '🔍'),
            'HELD': ('waiting', 'Waiting', '⏳'),
            'CONFIRMED': ('waiting', 'Processing', '⏳'),
        }
        cls, display, icon = status_map.get(status, ('investigating', 'Investigating', '🔍'))
        case_list.append({
            'case_id': str(c.case_id)[:12] + '...' if len(str(c.case_id)) > 12 else str(c.case_id),
            'title': c.title or 'Case',
            'status_class': cls,
            'status_display': display,
            'icon': icon,
            'category': 'internet',
            'time_ago': str(c.updated_at.strftime('%b %d, %H:%M')) if c.updated_at else '',
        })
    return render(request, 'consumer_home.html', {
        'cases': case_list,
        'user_name': request.session.get('consumer_name', 'there'),
        'user_initial': (request.session.get('consumer_name', 'U')[:1]).upper(),
        'time_of_day': 'morning',
    })


def consumer_report(request):
    return render(request, 'consumer_report.html')


def consumer_case_detail(request, case_id):
    from apps.agreements.models import Case
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'consumer_case.html', {
            'case_id': case_id, 'title': 'Case Not Found',
            'status_display': 'Not Found', 'status_class': '', 'status_icon': '❓',
        })
    status = case.status or 'SUBMITTED'
    status_map = {
        'SETTLED': ('resolved', 'Resolved', '✅'),
        'CANCELLED': ('resolved', 'Cancelled', '✅'),
        'DISPUTED': ('investigating', 'Investigating', '🔍'),
        'HELD': ('waiting', 'Waiting', '⏳'),
    }
    cls, display, icon = status_map.get(status, ('investigating', 'Investigating', '🔍'))
    timeline = [
        {'time': case.created_at.strftime('%H:%M') if case.created_at else '', 'text': 'Case created', 'icon': '📋', 'dot_class': 'system'},
        {'time': case.created_at.strftime('%H:%M') if case.created_at else '', 'text': 'Context assembly initiated', 'icon': '🔗', 'dot_class': 'system'},
        {'time': '', 'text': 'Diagnosis in progress', 'icon': '🔍', 'dot_class': 'info'},
    ]
    if status == 'SETTLED':
        timeline.append({'time': case.updated_at.strftime('%H:%M') if case.updated_at else '', 'text': 'Issue resolved', 'icon': '✅', 'dot_class': 'success'})
    return render(request, 'consumer_case.html', {
        'case_id': str(case.case_id),
        'title': case.title or 'Case',
        'status_display': display,
        'status_class': cls,
        'status_icon': icon,
        'category': 'General',
        'provider': '—',
        'created_at': case.created_at.strftime('%b %d, %Y %H:%M') if case.created_at else '',
        'timeline': timeline,
        'show_feedback': status not in ['SETTLED', 'CANCELLED'],
    })


def consumer_cases(request):
    return consumer_home(request)


def consumer_activity(request):
    return render(request, 'consumer_activity.html', {'activities': []})


def consumer_profile(request):
    return render(request, 'consumer_profile.html', {
        'user_name': 'User',
        'user_initial': 'U',
        'user_email': 'user@example.com',
    })


urlpatterns = [
    path('', home),

    # Consumer (public)
    path('report/', consumer_signin, name='consumer-signin'),
    path('report/signin/', consumer_signin, name='consumer-signin-alt'),
    path('report/verify/', consumer_verify, name='consumer-verify'),
    path('portal/auth/email/', consumer_auth_email, name='consumer-auth-email'),
    path('portal/auth/google/', consumer_auth_google, name='consumer-auth-google'),
    path('portal/auth/linkedin/', consumer_auth_linkedin, name='consumer-auth-linkedin'),
    path('portal/auth/verify/', consumer_verify_phone, name='consumer-auth-verify'),
    path('portal/consumer/', consumer_home, name='consumer-home'),
    path('portal/consumer/report/', consumer_report, name='consumer-report'),
    path('portal/consumer/case/<str:case_id>/', consumer_case_detail, name='consumer-case'),
    path('portal/consumer/cases/', consumer_cases, name='consumer-cases'),
    path('portal/consumer/activity/', consumer_activity, name='consumer-activity'),
    path('portal/consumer/profile/', consumer_profile, name='consumer-profile'),

    path('django-admin/', admin.site.urls),

    # === V1 Developer API (the product) ===
    path('api/v1/', include('apps.api_v1.urls')),

    # === Core Engine APIs (internal/backward compat) ===
    path('api/cases/',  include('apps.agreements.urls')),
    path('api/conditions/',  include('apps.conditions.urls')),
    path('api/ledger/',     include('apps.ledger.urls')),
    path('api/settlements/', include('apps.settlements.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/payments/', include('apps.payments.urls_api')),

    # Payment Provider Webhooks
    path('webhooks/', include('apps.payments.urls')),

    # TrustLayer Operations Dashboard (IP-whitelisted, separate auth)
    path('admin/', include('apps.admin_dashboard.urls')),

    # Customer Portal
    path('portal/', include('apps.customer_portal.urls')),

    # === API Docs (custom branded page) ===
    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/docs/', docs_redirect, name='docs-redirect'),
    path('docs/', docs_redirect, name='docs-redirect-alt'),

    # Engine Test APIs (no auth required — designed for testing)
    path('api/engines/<str:engine_id>/test/', engine_test, name='api-engine-test'),
    path('api/engines/provider/<str:provider_id>/test/', provider_test, name='api-provider-test'),

    # AT Marketplace (no auth)
    path('health/', health_json, name='health'),
    path('manifest/', manifest_view, name='manifest'),

    # Internal Health / Infrastructure (IP-whitelisted)
    path('internal/health/', health_json, name='internal-health'),
    path('internal/containers/', containers_json, name='internal-containers'),
]