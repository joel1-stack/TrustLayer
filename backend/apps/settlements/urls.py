from django.urls import path
from . import views

urlpatterns = [
    path('agreement/<str:agreement_id>/', views.list_settlements, name='list-settlements'),
    path('agreement/<str:agreement_id>/trigger/', views.trigger_settlement, name='trigger-settlement'),
]