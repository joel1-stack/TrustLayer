"""
TrustLayer Root URL Configuration — Core Engine APIs + Admin Dashboard + Internal.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from apps.admin_dashboard.views.infrastructure import health_json, containers_json


def home(request):
    return JsonResponse({
        'service': 'TrustLayer',
        'version': '2.0',
        'status': 'operational',
        'engines': ['agreements', 'state_machine', 'conditions', 'ledger', 'settlements', 'notifications', 'orchestration'],
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

    # Payment Provider Webhooks (Direction 2: Provider → TrustLayer)
    path('webhooks/', include('apps.payments.urls')),

    # Developer API — generate payment link
    path('api/payments/', include('apps.payments.urls_api')),

    # TrustLayer Operations Dashboard (IP-whitelisted, separate auth)
    path('admin/', include('apps.admin_dashboard.urls')),

    # Customer Portal
    path('portal/', include('apps.customer_portal.urls')),

    # Internal Health / Infrastructure (IP-whitelisted)
    path('internal/health/', health_json, name='internal-health'),
    path('internal/containers/', containers_json, name='internal-containers'),
]
