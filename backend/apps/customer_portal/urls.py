from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.portal_login, name='portal-login'),
    path('logout/', views.portal_logout, name='portal-logout'),
    path('verify/pending/', views.verify_pending, name='portal-verify-pending'),
    path('verify/send/', views.verify_send_email, name='portal-verify-send'),
    path('verify/confirm/<str:token>/', views.verify_confirm, name='portal-verify-confirm'),
    path('', views.portal_home, name='portal-home'),
    path('agreements/', views.portal_agreements, name='portal-agreements'),
    path('ledger/', views.portal_ledger, name='portal-ledger'),
    path('settlements/', views.portal_settlements, name='portal-settlements'),
    path('developers/', views.portal_developers, name='portal-developers'),
    path('engines/', views.portal_engines, name='portal-engines'),
    path('settings/', views.portal_settings, name='portal-settings'),
    path('team/<str:member_id>/toggle/', views.portal_toggle_member, name='portal-team-toggle'),
    path('contact/', views.portal_contact, name='portal-contact'),
]
