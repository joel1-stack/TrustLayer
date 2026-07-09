from django.urls import path
from . import views

urlpatterns = [
    path('', views.portal_home, name='portal-home'),
    path('agreements/', views.portal_agreements, name='portal-agreements'),
    path('ledger/', views.portal_ledger, name='portal-ledger'),
    path('settlements/', views.portal_settlements, name='portal-settlements'),
    path('developers/', views.portal_developers, name='portal-developers'),
    path('settings/', views.portal_settings, name='portal-settings'),
]
