from django.urls import path
from . import views

urlpatterns = [
    path('stats/',   views.dashboard_stats, name='ledger-stats'),
    path('wallet/<str:phone>/', views.wallet_balance, name='ledger-wallet'),
]
