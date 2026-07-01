"""
TrustLayer Root URL Configuration — API protocol + Merchant Portal.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import render


def portal_dashboard(request):
    return render(request, 'portal/dashboard.html')

def portal_cashier(request):
    return render(request, 'portal/cashier.html')

def portal_onboard(request):
    return render(request, 'portal/onboard.html')


def portal_pay(request, token):
    return render(request, 'portal/pay.html', {'token': token})


urlpatterns = [
    path('', include('apps.portal.urls')),

    path('portal/dashboard/', portal_dashboard, name='portal-dashboard'),
    path('portal/cashier/',   portal_cashier,   name='portal-cashier'),
    path('portal/onboard/',   portal_onboard,   name='portal-onboard'),
    path('pay/<path:token>/', portal_pay, name='portal-pay'),

    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/merchants/',  include('apps.merchants.urls')),
    path('api/v1/sessions/',   include('apps.jwtsessions.urls')),
    path('api/v1/pay/',        include('apps.payments.urls')),
    path('api/v1/deals/',      include('apps.escrow.urls')),
    path('api/v1/ledger/',     include('apps.ledger.urls')),
    path('api/v1/settle/',     include('apps.settlements.urls')),
    path('api/v1/disputes/',   include('apps.disputes.urls')),
    path('api/v1/webhooks/',   include('apps.webhooks.urls')),
    path('api/v1/trust/',      include('apps.trust_scoring.urls')),

    # Legal pages
    path('terms/',          lambda r: render(r, 'legal/terms.html'),          name='terms'),
    path('dispute-policy/', lambda r: render(r, 'legal/dispute_policy.html'), name='dispute-policy'),
]
