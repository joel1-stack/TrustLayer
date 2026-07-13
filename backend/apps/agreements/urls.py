from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_or_create_agreement, name='agreement-list-create'),
    path('<str:agreement_id>/', views.get_agreement, name='agreement-detail'),
    path('<str:agreement_id>/kyc/approve/', views.approve_kyc, name='agreement-kyc-approve'),
    path('<str:agreement_id>/kyc/reject/', views.reject_kyc, name='agreement-kyc-reject'),
]