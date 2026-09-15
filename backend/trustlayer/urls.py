"""
TrustLayer Root URL Configuration
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.agreements import web_views as web

urlpatterns = [
    path('', web.home, name='home'),
    path('how-it-works/', web.how_it_works, name='how-it-works'),
    path('features/', web.features_page, name='features'),
    path('about/', web.about_page, name='about'),
    path('login/', web.login_page, name='login'),
    path('logout/', web.logout_page, name='logout'),
    path('report/', web.report_page, name='report'),
    path('report/submit/', web.report_submit, name='report-submit'),
    path('case/<str:case_id>/', web.case_detail, name='case-detail'),
    path('case/<str:case_id>/verify/', web.case_verify_page, name='case-verify'),
    path('case/<str:case_id>/confirm/', web.case_confirm, name='case-confirm'),
    path('case/<str:case_id>/message/', web.case_add_message, name='case-message'),
    path('track/', web.case_track, name='track'),
    path('admin/', web.admin_dashboard, name='admin-dashboard'),
    path('admin/logout/', web.logout_page, name='admin-logout'),
    path('admin/case/<str:case_id>/', web.admin_case, name='admin-case'),
    path('admin/case/<str:case_id>/message/', web.admin_case_add_message, name='admin-case-message'),
    path('django-admin/', admin.site.urls),
    path('api/v1/', include('apps.api_v1.urls')),
    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('health/', lambda r: JsonResponse({'status': 'ok'})),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
