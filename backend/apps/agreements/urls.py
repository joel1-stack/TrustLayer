from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_agreement, name='agreement-create'),
    path('<str:agreement_id>/', views.get_agreement, name='agreement-detail'),
]