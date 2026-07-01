"""
Ledger Models — Double-entry accounting.
Every financial event is recorded as a JournalEntry on an Account.
Debits must always equal Credits. No exceptions.
"""
from django.db import models
from django.conf import settings
import uuid


class Account(models.Model):
    ACCOUNT_TYPES = [
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
        ('REVENUE', 'Revenue'),
        ('EXPENSE', 'Expense'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='KES')
    is_system = models.BooleanField(default=False, help_text='System-managed account (e.g. float, fees)')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ledger_accounts'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.account_type}) — KES {self.balance}"


class LedgerTransaction(models.Model):
    TXN_STATUS = [
        ('PENDING', 'Pending'),
        ('SETTLED', 'Settled'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    TXN_TYPES = [
        ('PAYMENT', 'Payment'),
        ('REFUND', 'Refund'),
        ('PAYOUT', 'Payout'),
        ('FEE', 'Fee'),
        ('ESCROW_HOLD', 'Escrow Hold'),
        ('ESCROW_RELEASE', 'Escrow Release'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_id = models.CharField(max_length=255, unique=True, db_index=True, help_text='External reference (invoice, M-Pesa receipt)')
    txn_type = models.CharField(max_length=20, choices=TXN_TYPES)
    status = models.CharField(max_length=20, choices=TXN_STATUS, default='PENDING')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    description = models.CharField(max_length=500, blank=True)
    merchant = models.ForeignKey('merchants.Merchant', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_txns')
    provider = models.CharField(max_length=50, blank=True, help_text='e.g. intasend, mpesa')
    provider_tx_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ledger_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference_id']),
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.txn_type} {self.reference_id} — KES {self.amount} ({self.status})"


class JournalEntry(models.Model):
    ENTRY_TYPES = [
        ('DEBIT', 'Debit'),
        ('CREDIT', 'Credit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(LedgerTransaction, on_delete=models.CASCADE, related_name='entries')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='entries')
    entry_type = models.CharField(max_length=6, choices=ENTRY_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    description = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_journal_entries'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['transaction']),
            models.Index(fields=['account']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.entry_type} KES {self.amount} — {self.account.name}"


class Wallet(models.Model):
    """
    Every user (merchant, customer) gets a Wallet.
    The wallet is just a pointer to a Liability Account.
    Balance = how much of the float belongs to this user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_phone = models.CharField(max_length=20, unique=True, db_index=True)
    owner_name = models.CharField(max_length=255, blank=True)
    owner_type = models.CharField(max_length=20, choices=[('MERCHANT', 'Merchant'), ('CUSTOMER', 'Customer')], default='CUSTOMER')
    account = models.OneToOneField(Account, on_delete=models.PROTECT, related_name='wallet')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ledger_wallets'

    @property
    def balance(self):
        return self.account.balance

    def __str__(self):
        return f"Wallet {self.owner_phone} — KES {self.balance}"
