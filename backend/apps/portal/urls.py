from django.urls import path
from django.shortcuts import render
from . import views, dashboard_views

urlpatterns = [
    path('', views.index, name='portal-index'),
    path('register/', views.register_ajax, name='portal-register-ajax'),
    path('login/', views.login_ajax, name='portal-login-ajax'),
    path('api/stats/', dashboard_views.business_stats, name='portal-stats'),
    path('api/proxy/deals/', dashboard_views.portal_deals, name='portal-proxy-deals'),
    path('api/proxy/collect/', dashboard_views.portal_collect, name='portal-proxy-collect'),
    path('api/proxy/withdraw/', dashboard_views.portal_withdraw, name='portal-proxy-withdraw'),
    path('api/proxy/create-session/', dashboard_views.portal_create_session, name='portal-proxy-create-session'),
    path('api/proxy/cashier-login/', dashboard_views.cashier_pin_login, name='portal-cashier-login'),
    path('api/proxy/businesses/', dashboard_views.portal_org_businesses, name='portal-businesses'),
    path('api/proxy/businesses/update/', dashboard_views.portal_update_business, name='portal-business-update'),
]
