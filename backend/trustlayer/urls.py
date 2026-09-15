"""
TrustLayer Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render, redirect
from django.utils import timezone
from apps.admin_dashboard.views.infrastructure import health_json, containers_json
from apps.admin_dashboard.views.engines import engine_test
from apps.core.marketplace import manifest_view
from apps.agreements.models import Case
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from apps.admin_dashboard.views.docs import docs_view


def home(request):
    today = timezone.now().date()
    total_cases = Case.objects.count()
    from apps.core.constants import STATUS_CATEGORIES
    terminal_states = [s for s, c in STATUS_CATEGORIES.items() if c == 'terminal']
    active_cases = Case.objects.exclude(status__in=terminal_states).count()
    resolved_today = Case.objects.filter(status='SETTLED', updated_at__date=today).count()
    total_closed_today = Case.objects.filter(status__in=terminal_states, updated_at__date=today).count()
    auto_resolved_rate = f"{round((resolved_today / total_closed_today) * 100)}%" if total_closed_today > 0 else "—"

    return render(request, 'landing.html', {
        'total_cases': total_cases,
        'active_cases': active_cases,
        'resolved_today': resolved_today,
        'auto_resolved_rate': auto_resolved_rate,
    })


def docs_redirect(request):
    return redirect('/admin/docs/')


# Consumer portal views
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
    cases = Case.objects.order_by('-updated_at')[:10]
    case_list = []
    for c in cases:
        status = c.status or 'SUBMITTED'
        status_map = {
            'SETTLED': ('resolved', 'Resolved'),
            'CANCELLED': ('resolved', 'Resolved'),
            'FAILED': ('resolved', 'Resolved'),
            'DISPUTED': ('investigating', 'Investigating'),
            'HELD': ('waiting', 'Waiting'),
            'CONFIRMED': ('waiting', 'Processing'),
        }
        cls, display = status_map.get(status, ('investigating', 'Investigating'))
        org_name = c.organization.name if c.organization else ''
        case_list.append({
            'case_id': str(c.case_id)[:12] + '...' if len(str(c.case_id)) > 12 else str(c.case_id),
            'title': c.title or 'Case',
            'status_class': cls,
            'status_display': display,
            'organization': org_name,
            'time_ago': str(c.updated_at.strftime('%b %d, %H:%M')) if c.updated_at else '',
        })
    return render(request, 'consumer_home.html', {
        'cases': case_list,
        'user_name': request.session.get('consumer_name', 'there'),
        'user_initial': (request.session.get('consumer_name', 'U')[:1]).upper(),
    })

def consumer_report(request):
    from apps.organizations.models import Organization
    orgs = Organization.objects.filter(status='ACTIVE')
    return render(request, 'consumer_report.html', {'organizations': orgs})

def consumer_case_detail(request, case_id):
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return render(request, 'consumer_case.html', {
            'case_id': case_id, 'title': 'Case Not Found',
            'status_display': 'Not Found', 'status_class': '', 'status_icon': '❓',
        })
    status = case.status or 'SUBMITTED'
    status_map = {
        'SETTLED': ('resolved', 'Resolved'),
        'CANCELLED': ('resolved', 'Cancelled'),
        'DISPUTED': ('investigating', 'Investigating'),
        'HELD': ('waiting', 'Waiting'),
    }
    cls, display = status_map.get(status, ('investigating', 'Investigating'))
    org_name = case.organization.name if case.organization else ''
    timeline = [
        {'time': case.created_at.strftime('%H:%M') if case.created_at else '', 'text': 'Case created', 'icon': '📋', 'dot_class': 'system'},
        {'time': '', 'text': 'Context assembled', 'icon': '🔗', 'dot_class': 'system'},
        {'time': '', 'text': 'Diagnosis in progress', 'icon': '🔍', 'dot_class': 'info'},
    ]
    if status == 'SETTLED':
        timeline.append({'time': case.updated_at.strftime('%H:%M') if case.updated_at else '', 'text': 'Issue resolved', 'icon': '✅', 'dot_class': 'success'})
    return render(request, 'consumer_case.html', {
        'case_id': str(case.case_id),
        'title': case.title or 'Case',
        'status_display': display,
        'status_class': cls,
        'status_icon': '✅' if status == 'SETTLED' else '🔍',
        'organization': org_name,
        'intent': case.intent,
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
        'user_name': request.session.get('consumer_name', 'User'),
        'user_initial': (request.session.get('consumer_name', 'U')[:1]).upper(),
        'user_email': request.session.get('consumer_email', 'user@example.com'),
    })


urlpatterns = [
    path('', home),

    # Consumer portal
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

    # V2 API (organization-agnostic)
    path('api/v1/', include('apps.api_v1.urls')),

    # Admin dashboard
    path('admin/', include('apps.admin_dashboard.urls')),

    # Customer portal (legacy)
    path('portal/', include('apps.customer_portal.urls')),

    # API docs
    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/docs/', docs_redirect, name='docs-redirect'),
    path('docs/', docs_redirect, name='docs-redirect-alt'),

    # Engine test
    path('api/engines/<str:engine_id>/test/', engine_test, name='api-engine-test'),

    # Health / manifest
    path('health/', health_json, name='health'),
    path('manifest/', manifest_view, name='manifest'),
    path('internal/health/', health_json, name='internal-health'),
    path('internal/containers/', containers_json, name='internal-containers'),
]
