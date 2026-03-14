from django.db import models 
from django.contrib.auth.models import User 
 
 
class Transaction(models.Model): 
    STATUS_CHOICES = [ 
        ('pending', 'Pending'), 
        ('completed', 'Completed'), 
        ('failed', 'Failed'), 
    ] 
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    amount = models.DecimalField(max_digits=12, decimal_places=2) 
    currency = models.CharField(max_length=3, default='KES') 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending') 
    reference = models.CharField(max_length=100, unique=True) 
    description = models.TextField(blank=True) 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 
    class Meta: 
        db_table = 'transactions' 
        ordering = ['-created_at'] 
    def __str__(self): 
        return f"{self.reference} - {self.amount} {self.currency}" 
 
 
class Wallet(models.Model): 
    user = models.OneToOneField(User, on_delete=models.CASCADE) 
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) 
    currency = models.CharField(max_length=3, default='KES') 
    is_active = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 
    class Meta: 
        db_table = 'wallets' 
    def __str__(self): 
        return f"{self.user.username} - {self.balance} {self.currency}" 



class MpesaPayment(models.Model):
    """M-PESA STK Push payment record"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    transaction = models.OneToOneField(
        Transaction, 
        on_delete=models.CASCADE,
        related_name='mpesa_payment'
    )
    phone_number = models.CharField(max_length=15)
    checkout_request_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    merchant_request_id = models.CharField(max_length=100, null=True, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, null=True, blank=True)
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpesa_payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"M-PESA {self.checkout_request_id} - {self.status}"
