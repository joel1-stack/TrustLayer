"""
Settlement Services — Process payouts, queue settlements.
"""
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import Payout, BankAccount
from apps.ledger import services as ledger_services
from apps.payments.adapters.intasend import intasend
import logging

logger = logging.getLogger(__name__)


def queue_payout(merchant_phone, amount, method='intasend', destination=''):
    """
    Queue a payout from merchant's wallet to their phone/bank.
    """
    wallet = ledger_services.get_or_create_wallet(merchant_phone, owner_type='MERCHANT')
    if wallet.balance < amount:
        raise ValueError(f"Insufficient balance. Have {wallet.balance}, need {amount}")

    from apps.merchants.models import Merchant
    merchant = Merchant.objects.filter(phone=merchant_phone).first()

    with db_transaction.atomic():
        fee_percent = Decimal('0.00')
        fee = (amount * fee_percent).quantize(Decimal('0.01'))
        net = amount - fee

        payout = Payout.objects.create(
            merchant=merchant,
            amount=amount,
            fee=fee,
            net_amount=net,
            method=method,
            destination=destination or merchant_phone,
            status='QUEUED',
            scheduled_at=timezone.now(),
        )

        txn = ledger_services.release_from_escrow(
            reference_id=f'PAYOUT_{payout.id.hex[:8]}',
            merchant_phone=merchant_phone,
            amount=amount,
            fee_percent=Decimal('0'),
        )
        payout.ledger_txn = txn
        payout.save()

    return payout


def process_payout(payout_id):
    """
    Send a queued payout via IntaSend.
    """
    try:
        payout = Payout.objects.get(id=payout_id, status='QUEUED')
    except Payout.DoesNotExist:
        return {'success': False, 'error': 'Payout not found or already processed'}

    payout.status = 'PROCESSING'
    payout.save()

    try:
        result = intasend.send_payout(
            phone=payout.destination,
            amount=int(payout.net_amount),
            name=payout.merchant.company_name if payout.merchant else 'Merchant',
        )
        payout.provider_tx_id = result.get('id', '')
        payout.status = 'SENT'
        payout.completed_at = timezone.now()
        payout.save()
        logger.info(f"Payout {payout_id} sent: {result}")
        return {'success': True, 'payout_id': str(payout.id)}
    except Exception as e:
        payout.status = 'FAILED'
        payout.failure_reason = str(e)
        payout.save()
        logger.error(f"Payout {payout_id} failed: {e}")
        return {'success': False, 'error': str(e)}
