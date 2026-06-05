"""
Escrow Deal Models
Every deal belongs to a merchant. No exceptions.
"""
from django.db import models
import uuid


class EscrowDeal(models.Model):
    STATUS_CHOICES = [
        ('PENDING',            'Pending'),
        ('PAYMENT_INITIATED',  'Payment Initiated'),
        ('HELD',               'Held'),
        ('DELIVERED',          'Delivered'),
        ('RELEASED',           'Released'),
        ('REFUNDED',           'Refunded'),
        ('DISPUTED',           'Disputed'),
        ('RESOLVED',           'Resolved'),
        ('EXPIRED',            'Expired'),
    ]

    LEDGER_STATUS_CHOICES = [
        ('UNPAID',          'Buyer has not paid'),
        ('HELD',            'Funds in paybill, not yet released'),
        ('RELEASE_PENDING', 'B2C initiated, waiting for Safaricom'),
        ('RELEASED',        'Funds sent to seller'),
        ('STUCK',           'B2C failed, manual intervention needed'),
    ]

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.CASCADE,
        related_name='deals',
    )

    deal_code     = models.CharField(max_length=20, unique=True, db_index=True)
    session_token = models.TextField(blank=True, db_index=False)

    amount      = models.DecimalField(max_digits=15, decimal_places=2)
    fee_amount  = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency    = models.CharField(max_length=3, default='KES')
    description = models.CharField(max_length=500)

    buyer_phone = models.CharField(max_length=20)
    buyer_email = models.EmailField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    buyer_confirmed     = models.BooleanField(default=False)
    seller_confirmed    = models.BooleanField(default=False)
    buyer_confirmed_at  = models.DateTimeField(null=True, blank=True)
    seller_confirmed_at = models.DateTimeField(null=True, blank=True)

    payment_transaction = models.ForeignKey(
        'payments.PaymentTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='escrow_deal',
    )
    mpesa_receipt = models.CharField(max_length=50, blank=True)

    auto_release_at = models.DateTimeField(null=True, blank=True)
    released_at     = models.DateTimeField(null=True, blank=True)
    disputed_at     = models.DateTimeField(null=True, blank=True)
    dispute_reason  = models.TextField(blank=True)

    # Money tracking (what Safaricom holds vs what we've released)
    amount_paid      = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_released  = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    fee_charged      = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # B2C tracking
    b2c_conversation_id = models.CharField(max_length=100, blank=True, db_index=True)
    b2c_transaction_id  = models.CharField(max_length=100, blank=True)
    b2c_completed_at    = models.DateTimeField(null=True, blank=True)
    b2c_failure_reason  = models.TextField(blank=True)

    # Ledger state (separate from escrow state machine)
    ledger_status = models.CharField(
        max_length=20,
        choices=LEDGER_STATUS_CHOICES,
        default='UNPAID',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'escrow_deals'
        indexes  = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['deal_code']),
            models.Index(fields=['buyer_phone']),
            models.Index(fields=['created_at']),
            models.Index(fields=['b2c_conversation_id']),
            models.Index(fields=['ledger_status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.deal_code} — {self.status} — KES {self.amount}"


class FeeRecord(models.Model):
    """
    Each released deal generates one fee record — TrustLayer's revenue.
    """
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deal      = models.ForeignKey(EscrowDeal, on_delete=models.CASCADE, related_name='fees')
    amount    = models.DecimalField(max_digits=15, decimal_places=2)
    rate      = models.DecimalField(max_digits=5, decimal_places=2, default=1.50)
    currency  = models.CharField(max_length=3, default='KES')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fee_records'
        ordering = ['-created_at']

    def __str__(self):
        return f"Fee {self.amount} KES — deal {self.deal.deal_code}"
