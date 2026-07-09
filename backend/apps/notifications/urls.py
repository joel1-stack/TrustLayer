from django.urls import path
from . import views

urlpatterns = [
    path('agreement/<str:agreement_id>/', views.list_notifications, name='list-notifications'),
]