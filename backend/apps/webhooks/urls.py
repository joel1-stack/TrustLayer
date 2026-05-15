from django.urls import path
from . import views

urlpatterns = [
    path('register/',              views.register_webhook, name='register_webhook'),
    path('list/',                  views.list_webhooks,    name='list_webhooks'),
    path('delete/<str:webhook_id>/', views.delete_webhook, name='delete_webhook'),
    path('logs/<str:webhook_id>/', views.delivery_logs,   name='delivery_logs'),
]
