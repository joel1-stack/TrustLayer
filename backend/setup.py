import os

models = open('/app/api/models.py','w')
models.write("""from django.db import models as django_models
from django.contrib.auth.models import User
from decimal import Decimal
import random, string

FEE_RATE = Decimal('0.015')

def generate_deal_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = 'TL-' + ''.join(random.choices(chars, k=6))
        if not Escrow.objects.filter(deal_code=code).exists():
            return code

class Transaction(django_models.Model):
    STATUS_CHOICES = [('pending','Pending'),('completed','Completed'),('failed','Failed')]
    user = django_models.ForeignKey(User, on_delete=django_models.CASCADE)
    amount = django_models.DecimalField(max_digits=12, decimal_places=2)
    currency = django_models.CharField(max_length=3, default='KES')
    status = django_models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = django_models.CharField(max_length=100, unique=True)
    description = django_models.TextField(blank=True)
    created_at = django_models.DateTimeField(auto_now_add=True)
    updated_at = django_models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
    def __str__(self):
        return f'{self.reference} - {self.amount} {self.currency}'

class Wallet(django_models.Model):
    user = django_models.OneToOneField(User, on_delete=django_models.CASCADE)
    balance = django_models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = django_models.CharField(max_length=3, default='KES')
    is_active = django_models.BooleanField(default=True)
    created_at = django_models.DateTimeField(auto_now_add=True)
    updated_at = django_models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'wallets'
    def __str__(self):
        return f'{self.user.username} - {self.balance} {self.currency}'

class MpesaPayment(django_models.Model):
    STATUS_CHOICES = [('pending','Pending'),('processing','Processing'),('completed','Completed'),('failed','Failed'),('cancelled','Cancelled')]
    transaction = django_models.OneToOneField(Transaction, on_delete=django_models.CASCADE, related_name='mpesa_payment')
    phone_number = django_models.CharField(max_length=15)
    checkout_request_id = django_models.CharField(max_length=100, unique=True, null=True, blank=True)
    merchant_request_id = django_models.CharField(max_length=100, null=True, blank=True)
    mpesa_receipt_number = django_models.CharField(max_length=50, null=True, blank=True)
    result_code = django_models.IntegerField(null=True, blank=True)
    result_desc = django_models.TextField(null=True, blank=True)
    status = django_models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = django_models.DateTimeField(auto_now_add=True)
    updated_at = django_models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'mpesa_payments'
        ordering = ['-created_at']
    def __str__(self):
        return f'M-PESA {self.checkout_request_id} - {self.status}'

class Escrow(django_models.Model):
    STATE_PENDING = 'pending'
    STATE_HELD = 'held'
    STATE_DONE = 'done'
    STATE_REFUNDED = 'refunded'
    STATE_CHOICES = [('pending','Pending'),('held','Held'),('done','Done'),('refunded','Refunded')]
    deal_code = django_models.CharField(max_length=10, unique=True, editable=False, db_index=True)
    sender = django_models.ForeignKey(User, related_name='escrow_sent', on_delete=django_models.CASCADE)
    receiver = django_models.ForeignKey(User, related_name='escrow_received', on_delete=django_models.SET_NULL, null=True, blank=True)
    amount = django_models.DecimalField(max_digits=12, decimal_places=2)
    fee = django_models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=Decimal('0.00'))
    state = django_models.CharField(max_length=10, choices=STATE_CHOICES, default='pending')
    description = django_models.TextField(blank=True)
    mpesa_checkout_id = django_models.CharField(max_length=100, blank=True, null=True)
    mpesa_receipt = django_models.CharField(max_length=50, blank=True, null=True)
    created_at = django_models.DateTimeField(auto_now_add=True)
    updated_at = django_models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'escrows'
        ordering = ['-created_at']
    def save(self, *args, **kwargs):
        if not self.deal_code:
            self.deal_code = generate_deal_code()
        self.fee = (Decimal(str(self.amount)) * FEE_RATE).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
    def __str__(self):
        return f'{self.deal_code} | KES {self.amount} | {self.state}'
    @property
    def total_payable(self):
        return Decimal(str(self.amount)) + Decimal(str(self.fee))
    def mark_held(self, mpesa_checkout_id=None, mpesa_receipt=None):
        if self.state != self.STATE_PENDING:
            raise ValueError(f'Cannot move to held from {self.state}')
        from django.db import transaction
        with transaction.atomic():
            if mpesa_checkout_id: self.mpesa_checkout_id = mpesa_checkout_id
            if mpesa_receipt: self.mpesa_receipt = mpesa_receipt
            self.state = self.STATE_HELD
            self.save()
    def mark_done(self):
        if self.state != self.STATE_HELD:
            raise ValueError(f'Cannot release from {self.state}')
        from django.db import transaction
        with transaction.atomic():
            self.state = self.STATE_DONE
            self.save()
    def mark_refunded(self):
        if self.state != self.STATE_HELD:
            raise ValueError(f'Can only refund from held. Current: {self.state}')
        from django.db import transaction
        with transaction.atomic():
            self.state = self.STATE_REFUNDED
            self.save()

class WebhookLog(django_models.Model):
    escrow = django_models.ForeignKey(Escrow, on_delete=django_models.SET_NULL, null=True, blank=True, related_name='webhook_logs')
    event = django_models.CharField(max_length=100)
    payload = django_models.JSONField()
    created_at = django_models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'webhook_logs'
        ordering = ['-created_at']
    def __str__(self):
        return f'[{self.event}] escrow={self.escrow_id}'
""")
models.close()
print('models.py done')

urls = open('/app/api/urls.py','w')
urls.write("""from django.urls import path, include
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
""")
urls.close()
print('urls.py done')
print('ALL DONE - now run: python manage.py makemigrations api && python manage.py migrate')