from django.urls import path
from . import views

urlpatterns = [
    path('cases/', views.list_cases_api, name='v1-list-cases'),
    path('cases/create/', views.create_case_api, name='v1-create-case'),
    path('cases/<str:case_id>/', views.case_detail_api, name='v1-case-detail'),
    path('cases/<str:case_id>/evidence/', views.collect_evidence_api, name='v1-add-evidence'),
    path('cases/<str:case_id>/investigate/', views.start_investigation_api, name='v1-investigate'),
    path('cases/<str:case_id>/resolve/', views.resolve_case_api, name='v1-resolve'),
    path('cases/<str:case_id>/verify/', views.verify_case_api, name='v1-verify'),
    path('cases/<str:case_id>/confirm/', views.customer_verify_api, name='v1-customer-confirm'),
    path('cases/<str:case_id>/close/', views.close_case_api, name='v1-close'),
    path('cases/<str:case_id>/messages/', views.add_message_api, name='v1-add-message'),
]
