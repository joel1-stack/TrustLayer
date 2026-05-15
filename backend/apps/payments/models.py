"""
Payment Models — M-Pesa & Future Adapters
Every payment belongs to a merchant. No exceptions.
"""
from django.db import models
import uuid


class PaymentTransaction(models.Model):
    PROVIDER_CHOICES = [
        ('mpesa',   'M-Pesa Daraja'),
        ('pesapal', 'Pesapal'),
        ('equity',  'Equity Bank'),
        ('card',    'Card Payment'),
    ]

    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('initiated',  'Initiated'),
        ('processing', 'Processing'),
        ('success',    'Success'),
        ('failed',     'Failed'),
        ('cancelled',  'Cancelled'),
        ('refunded',   'Refunded'),
    ]

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.CASCADE,
        related_name='payments',
    )

    provider       = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='mpesa')
    provider_tx_id = models.CharField(max_length=100, blank=True, db_index=True)

    amount       = models.DecimalField(max_digits=15, decimal_places=2)
    currency     = models.CharField(max_length=3, default='KES')
    phone_number = models.CharField(max_length=20)
    description  = models.CharField(max_length=500, blank=True)

    # M-Pesa specific
    mpesa_receipt        = models.CharField(max_length=50, blank=True, db_index=True)
    checkout_request_id  = models.CharField(max_length=100, blank=True, db_index=True)
    merchant_request_id  = models.CharField(max_length=100, blank=True)
    result_code          = models.IntegerField(null=True, blank=True)
    result_desc          = models.CharField(max_length=255, blank=True)

    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    callback_received = models.BooleanField(default=False)
    callback_payload  = models.JSONField(default=dict, blank=True)

    deal_code = models.CharField(max_length=20, blank=True, db_index=True)

    initiated_at  = models.DateTimeField(auto_now_add=True)
    completed_at  = models.DateTimeField(null=True, blank=True)
    callback_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payment_transactions'
        indexes  = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['checkout_request_id']),
            models.Index(fields=['mpesa_receipt']),
            models.Index(fields=['deal_code']),
        ]
        ordering = ['-initiated_at']

    def __str__(self):
        return f"{self.provider.upper()} {self.amount} KES — {self.status}"
