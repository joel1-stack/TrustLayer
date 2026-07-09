from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_or_create_agreement, name='agreement-list-create'),
    path('<str:agreement_id>/', views.get_agreement, name='agreement-detail'),
]