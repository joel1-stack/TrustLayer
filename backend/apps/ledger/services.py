"""
Ledger Services — Create accounts, record transactions, split payments.
"""
from decimal import Decimal
from django.db import models, transaction as db_transaction
from django.utils import timezone
from .models import Account, LedgerTransaction, JournalEntry, Wallet
import logging

logger = logging.getLogger(__name__)


def ensure_system_accounts():
    """Create system accounts on first run."""
    accounts = {
        'IntaSend_Float': 'ASSET',
        'Platform_Fees': 'REVENUE',
        'Escrow_Hold': 'LIABILITY',
    }
    for name, atype in accounts.items():
        Account.objects.get_or_create(
            name=name,
            defaults={'account_type': atype, 'is_system': True},
        )


def get_or_create_wallet(phone, name='', owner_type='CUSTOMER'):
    """Get or create a wallet + liability account for a user."""
    try:
        wallet = Wallet.objects.get(owner_phone=phone)
        if not wallet.account_id:
            acc, _ = Account.objects.get_or_create(
                name=f'Wallet_{phone}',
                defaults={'account_type': 'LIABILITY', 'balance': 0},
            )
            wallet.account = acc
            wallet.save()
        return wallet
    except Wallet.DoesNotExist:
        acc, _ = Account.objects.get_or_create(
            name=f'Wallet_{phone}',
            defaults={'account_type': 'LIABILITY', 'balance': 0},
        )
        wallet = Wallet.objects.create(
            owner_phone=phone,
            owner_name=name,
            owner_type=owner_type,
            account=acc,
        )
        return wallet


def record_payment(reference_id, phone, amount, name='', provider='intasend', provider_tx_id='', description=''):
    """
    Record a successful payment in the ledger.
    Debit: IntaSend_Float (money is in our wallet)
    Credit: Customer's Wallet (we owe them this much)
    """
    ensure_system_accounts()

    with db_transaction.atomic():
        txn, created = LedgerTransaction.objects.get_or_create(
            reference_id=reference_id,
            defaults={
                'txn_type': 'PAYMENT',
                'status': 'SETTLED',
                'amount': amount,
                'description': description or f'Payment of KES {amount} from {phone}',
                'provider': provider,
                'provider_tx_id': provider_tx_id,
                'settled_at': timezone.now(),
            },
        )
        if not created:
            return txn

        float_acc = Account.objects.get(name='IntaSend_Float')
        wallet = get_or_create_wallet(phone, name)
        wallet_acc = wallet.account

        JournalEntry.objects.create(transaction=txn, account=float_acc, entry_type='DEBIT', amount=amount)
        JournalEntry.objects.create(transaction=txn, account=wallet_acc, entry_type='CREDIT', amount=amount)

        float_acc.balance += amount
        wallet_acc.balance += amount
        float_acc.save()
        wallet_acc.save()

    logger.info(f"Payment recorded: {reference_id} — KES {amount} from {phone}")
    return txn


def hold_in_escrow(reference_id, phone, amount, description=''):
    """
    Move funds from customer wallet to escrow.
    Debit: Customer Wallet
    Credit: Escrow_Hold
    """
    with db_transaction.atomic():
        txn = LedgerTransaction.objects.create(
            reference_id=f'HOLD_{reference_id}',
            txn_type='ESCROW_HOLD',
            status='PENDING',
            amount=amount,
            description=description,
        )
        wallet = Wallet.objects.get(owner_phone=phone)
        escrow_acc = Account.objects.get(name='Escrow_Hold')

        JournalEntry.objects.create(transaction=txn, account=wallet.account, entry_type='DEBIT', amount=amount)
        JournalEntry.objects.create(transaction=txn, account=escrow_acc, entry_type='CREDIT', amount=amount)

        wallet.account.balance -= amount
        escrow_acc.balance += amount
        wallet.account.save()
        escrow_acc.save()

    return txn


def release_from_escrow(reference_id, merchant_phone, amount, fee_percent=Decimal('0.05')):
    """
    Release escrow to merchant.
    1. Debit Escrow_Hold (remove from escrow)
    2. Credit Merchant Wallet (merchant gets paid - fee)
    3. Credit Platform_Fees (platform earns fee)
    """
    with db_transaction.atomic():
        fee_amount = (amount * fee_percent).quantize(Decimal('0.01'))
        merchant_amount = amount - fee_amount

        txn = LedgerTransaction.objects.create(
            reference_id=f'RELEASE_{reference_id}',
            txn_type='ESCROW_RELEASE',
            status='SETTLED',
            amount=merchant_amount,
            description=f'Release KES {merchant_amount} (fee: KES {fee_amount})',
            settled_at=timezone.now(),
        )

        escrow_acc = Account.objects.get(name='Escrow_Hold')
        fee_acc = Account.objects.get(name='Platform_Fees')
        merchant_wallet = get_or_create_wallet(merchant_phone, '', 'MERCHANT')

        JournalEntry.objects.create(transaction=txn, account=escrow_acc, entry_type='DEBIT', amount=amount)
        JournalEntry.objects.create(transaction=txn, account=merchant_wallet.account, entry_type='CREDIT', amount=merchant_amount)
        JournalEntry.objects.create(transaction=txn, account=fee_acc, entry_type='CREDIT', amount=fee_amount)

        escrow_acc.balance -= amount
        merchant_wallet.account.balance += merchant_amount
        fee_acc.balance += fee_amount
        escrow_acc.save()
        merchant_wallet.account.save()
        fee_acc.save()

    logger.info(f"Escrow released: {reference_id} — KES {merchant_amount} to {merchant_phone}")
    return txn


def get_dashboard_stats(merchant_phone=None):
    """Get stats for the dashboard."""
    ensure_system_accounts()

    float_acc = Account.objects.get(name='IntaSend_Float')
    fee_acc = Account.objects.get(name='Platform_Fees')
    escrow_acc = Account.objects.get(name='Escrow_Hold')

    stats = {
        'total_float': float(float_acc.balance),
        'platform_fees': float(fee_acc.balance),
        'in_escrow': float(escrow_acc.balance),
        'total_collected': float(LedgerTransaction.objects.filter(txn_type='PAYMENT', status='SETTLED').aggregate(models.Sum('amount'))['amount__sum'] or 0),
        'pending_payments': LedgerTransaction.objects.filter(status='PENDING').count(),
    }

    if merchant_phone:
        try:
            wallet = Wallet.objects.get(owner_phone=merchant_phone)
            stats['wallet_balance'] = float(wallet.balance)
        except Wallet.DoesNotExist:
            stats['wallet_balance'] = 0

    return stats
