"""
TrustLayer Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.http import JsonResponse


def checkout_page(request, token):
    return render(request, 'checkout/pay.html', {'token': token})

def success_page(request):
    return render(request, 'checkout/success.html')

def failure_page(request):
    return render(request, 'checkout/failure.html')

def merchant_dashboard(request):
    from apps.merchants.permissions import APIKeyAuthentication
    result = APIKeyAuthentication().authenticate(request)
    if not result:
        # Not authenticated — serve the login UI (JS handles auth)
        return render(request, 'dashboard/merchant_dashboard.html', {})
    merchant = result[0]
    return render(request, 'dashboard/merchant_dashboard.html', {
        'merchant':     merchant,
        'deals':        merchant.deals.all()[:20],
        'payments':     merchant.payments.all()[:20],
        'active_deals': merchant.deals.filter(status='HELD').count(),
    })


urlpatterns = [
    path('admin/', admin.site.urls),

    # Merchant API
    path('api/v1/merchants/', include('apps.merchants.urls')),

    # Session API
    path('api/v1/sessions/',  include('apps.jwtsessions.urls')),

    # Payment API (STK Push + Daraja callback)
    path('api/v1/pay/',       include('apps.payments.urls')),

    # Escrow API (deal status + confirm delivery)
    path('api/v1/deals/',     include('apps.escrow.urls')),
    path('api/v1/escrow/',    include('apps.escrow.urls')),

    # Disputes API
    path('api/v1/disputes/',  include('apps.disputes.urls')),

    # Webhooks API
    path('api/v1/webhooks/',  include('apps.webhooks.urls')),

    # Trust Scoring API
    path('api/v1/trust/',     include('apps.trust_scoring.urls')),

    # Short deal URL redirect — /d/TL-XXXXX/ → /pay/<token>/
    path('d/<str:deal_code>/', lambda r, deal_code: __import__('apps.escrow.views', fromlist=['short_deal_redirect']).short_deal_redirect(r, deal_code), name='short-deal'),

    # Buyer-facing checkout pages
    path('pay/<path:token>/',  checkout_page,      name='checkout'),
    path('pay/success/',      success_page,        name='checkout-success'),
    path('pay/failed/',       failure_page,        name='checkout-failed'),

    # Merchant dashboard
    path('dashboard/',        merchant_dashboard,  name='dashboard'),

    # Register page
    path('register/', lambda r: render(r, 'register.html'), name='register'),

    # Create deal page
    path('create-deal/', lambda r: render(r, 'create_deal.html'), name='create-deal'),

    # Legal pages
    path('terms/',          lambda r: render(r, 'legal/terms.html'),          name='terms'),
    path('dispute-policy/', lambda r: render(r, 'legal/dispute_policy.html'), name='dispute-policy'),

    # SDK embed demo — template deleted, route removed
    # path('embed-demo/', ...)
]
