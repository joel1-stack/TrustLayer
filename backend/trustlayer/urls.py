"""
TrustLayer Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render


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

    # Disputes API
    path('api/v1/disputes/',  include('apps.disputes.urls')),

    # Webhooks API
    path('api/v1/webhooks/',  include('apps.webhooks.urls')),

    # Trust Scoring API
    path('api/v1/trust/',     include('apps.trust_scoring.urls')),

    # Short deal URL redirect — /d/TL-XXXXX/ → /pay/<token>/
    path('d/<str:deal_code>/', lambda r, deal_code: __import__('apps.escrow.views', fromlist=['short_deal_redirect']).short_deal_redirect(r, deal_code), name='short-deal'),

    # Minimal payment page
    path('pay/<path:token>/', lambda r, token: render(r, 'checkout/pay.html', {'token': token}), name='checkout'),

    # Legal pages
    path('terms/',          lambda r: render(r, 'legal/terms.html'),          name='terms'),
    path('dispute-policy/', lambda r: render(r, 'legal/dispute_policy.html'), name='dispute-policy'),
]
