from django.urls import path
from . import views

urlpatterns = [
    path('agreement/<str:agreement_id>/', views.get_entries, name='get-ledger-entries'),
    path('balance/<int:party_id>/', views.get_balance, name='get-party-balance'),
]