"""
TrustLayer Root URL Configuration — V1 API + Swagger + Admin + Internal.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from apps.admin_dashboard.views.infrastructure import health_json, containers_json
from apps.admin_dashboard.views.engines import engine_test, provider_test
from apps.core.marketplace import manifest_view
from apps.agreements.models import Case as Agreement, CaseParty as AgreementParty
from apps.ledger.models import LedgerEntry
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def home(request):
    today = timezone.now().date()
    total_cases = Agreement.objects.count()
    settled_today = Agreement.objects.filter(status='SETTLED', updated_at__date=today).count()
    from apps.core.constants import STATUS_CATEGORIES
    terminal_states = [s for s, c in STATUS_CATEGORIES.items() if c == 'terminal']
    active = Agreement.objects.exclude(status__in=terminal_states).count()
    fees = LedgerEntry.objects.filter(
        entry_type='CREDIT', description__icontains='Platform'
    ).aggregate(t=Sum('amount'))['t'] or 0
    return render(request, 'landing.html', {
        'total_cases': total_cases,
        'settled_today': settled_today,
        'active_cases': active,
        'platform_fees': float(fees),
    })


urlpatterns = [
    path('', home),

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

    # === Swagger / OpenAPI Docs ===
    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

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