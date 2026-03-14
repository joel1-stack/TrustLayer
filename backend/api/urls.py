from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, WalletViewSet, TransactionViewSet
from .payment_views import PaymentViewSet, mpesa_callback

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('payments/callback/', mpesa_callback, name='mpesa-callback'),
]