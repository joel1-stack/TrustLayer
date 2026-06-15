"""
TrustLayer Root URL Configuration — API protocol only.
No HTML pages served beyond legal templates.
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

    # Payment API (STK Push + Daraja callback + B2C)
    path('api/v1/pay/',       include('apps.payments.urls')),

    # Escrow API (deal lifecycle)
    path('api/v1/deals/',     include('apps.escrow.urls')),

    # Disputes API
    path('api/v1/disputes/',  include('apps.disputes.urls')),

    # Webhooks API
    path('api/v1/webhooks/',  include('apps.webhooks.urls')),

    # Trust Scoring API
    path('api/v1/trust/',     include('apps.trust_scoring.urls')),

    # Legal pages (regulatory requirement)
    path('terms/',          lambda r: render(r, 'legal/terms.html'),          name='terms'),
    path('dispute-policy/', lambda r: render(r, 'legal/dispute_policy.html'), name='dispute-policy'),
]
