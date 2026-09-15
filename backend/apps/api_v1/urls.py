from django.urls import path
from . import views, views_v2

urlpatterns = [
    # V1 — Legacy escrow API
    path('cases/', views.list_cases_api, name='v1-list-cases'),
    path('cases/create/', views.create_case_api, name='v1-create-case'),
    path('cases/<str:case_id>/', views.case_detail_api, name='v1-case-detail'),

    # V2 — Organization-agnostic System of Action API
    path('v2/organizations/', views_v2.list_organizations, name='v2-list-organizations'),
    path('v2/organizations/detect/', views_v2.detect_organization, name='v2-detect-organization'),
    path('v2/cases/', views_v2.create_operational_case, name='v2-create-case'),
    path('v2/cases/<str:case_id>/', views_v2.case_status, name='v2-case-status'),
    path('v2/cases/<str:case_id>/timeline/', views_v2.case_timeline, name='v2-case-timeline'),
    path('v2/cases/<str:case_id>/feedback/', views_v2.verify_resolution, name='v2-case-feedback'),
]