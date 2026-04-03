from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, WalletViewSet, TransactionViewSet
from .payment_views import PaymentViewSet, mpesa_callback
from .nano_views import nano_create_deal, nano_pay, nano_deal_status, nano_release, nano_mpesa_callback

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('payments/callback/', mpesa_callback, name='mpesa-callback'),
    path('nano/deals/', nano_create_deal, name='nano-create-deal'),
    path('nano/pay/', nano_pay, name='nano-pay'),
    path('nano/deals/<str:deal_code>/', nano_deal_status, name='nano-deal-status'),
    path('nano/deals/<str:deal_code>/release/', nano_release, name='nano-release'),
    path('nano/callback/', nano_mpesa_callback, name='nano-callback'),
]
