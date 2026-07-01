"""
Settlement Models — Payout queue, bank accounts, settlement schedules.
"""
from django.db import models
import uuid


class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey('merchants.Merchant', on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    branch_code = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'settlement_bank_accounts'

    def __str__(self):
        return f"{self.bank_name} — {self.account_name} ({self.account_number[-4:]})"


class Payout(models.Model):
    PAYOUT_STATUS = [
        ('QUEUED', 'Queued'),
        ('PROCESSING', 'Processing'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYOUT_METHODS = [
        ('mpesa', 'M-Pesa B2C'),
        ('bank', 'Bank Transfer'),
        ('intasend', 'IntaSend Payout'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey('merchants.Merchant', on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=15, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYOUT_METHODS)
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS, default='QUEUED')
    destination = models.CharField(max_length=100, help_text='Phone number or bank account ref')
    provider_tx_id = models.CharField(max_length=255, blank=True)
    failure_reason = models.TextField(blank=True)
    ledger_txn = models.ForeignKey('ledger.LedgerTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='payouts')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'settlement_payouts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Payout KES {self.net_amount} to {self.destination} ({self.status})"
