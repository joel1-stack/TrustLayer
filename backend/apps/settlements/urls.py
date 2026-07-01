from django.urls import path
from . import views

urlpatterns = [
    path('queue/',   views.queue_payout_view, name='settle-queue'),
    path('process/', views.process_payout_view, name='settle-process'),
]
