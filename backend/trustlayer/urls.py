"""
TrustLayer Root URL Configuration — Landing + APIs + Admin + Internal.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from apps.admin_dashboard.views.infrastructure import health_json, containers_json
from apps.admin_dashboard.views.engines import engine_test, provider_test
from apps.agreements.models import Agreement, AgreementParty
from apps.ledger.models import LedgerEntry


def home(request):
    today = timezone.now().date()
    total_agreements = Agreement.objects.count()
    settled_today = Agreement.objects.filter(status='SETTLED', updated_at__date=today).count()
    from apps.agreements.models import STATUS_CATEGORIES
    terminal_states = [s for s, c in STATUS_CATEGORIES.items() if c == 'terminal']
    active = Agreement.objects.exclude(status__in=terminal_states).count()
    fees = LedgerEntry.objects.filter(
        entry_type='CREDIT', description__icontains='Platform'
    ).aggregate(t=Sum('amount'))['t'] or 0
    return render(request, 'landing.html', {
        'total_agreements': total_agreements,
        'settled_today': settled_today,
        'active_agreements': active,
        'platform_fees': float(fees),
    })


urlpatterns = [
    path('', home),

    path('django-admin/', admin.site.urls),

    # Core Engine APIs
    path('api/agreements/',  include('apps.agreements.urls')),
    path('api/conditions/',  include('apps.conditions.urls')),
    path('api/ledger/',     include('apps.ledger.urls')),
    path('api/settlements/', include('apps.settlements.urls')),
    path('api/notifications/', include('apps.notifications.urls')),

    # Payment Provider Webhooks
    path('webhooks/', include('apps.payments.urls')),

    # Developer API — generate payment link
    path('api/payments/', include('apps.payments.urls_api')),

    # TrustLayer Operations Dashboard (IP-whitelisted, separate auth)
    path('admin/', include('apps.admin_dashboard.urls')),

    # Customer Portal
    path('portal/', include('apps.customer_portal.urls')),

    # Engine Test APIs (no auth required — designed for testing)
    path('api/engines/<str:engine_id>/test/', engine_test, name='api-engine-test'),
    path('api/engines/provider/<str:provider_id>/test/', provider_test, name='api-provider-test'),

    # Internal Health / Infrastructure (IP-whitelisted)
    path('internal/health/', health_json, name='internal-health'),
    path('internal/containers/', containers_json, name='internal-containers'),
]
