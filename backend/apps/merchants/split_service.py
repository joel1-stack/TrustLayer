"""
Split Engine — Splits payments between parties automatically.
When a payment arrives, this service:
1. Finds the organization's split rules
2. Computes each party's share
3. Records splits in the ledger
4. Queues settlements to each destination
"""
import logging
from decimal import Decimal
from django.db import transaction as db_transaction
from .models import Organization, SplitRule

logger = logging.getLogger(__name__)


def get_split_rules(organization):
    """Get active split rules for an organization, ordered by priority."""
    return SplitRule.objects.filter(
        organization=organization, is_active=True
    ).order_by('-priority')


def compute_splits(organization, gross_amount):
    """
    Compute how 'gross_amount' should be split.
    Returns list of dicts: [{'name':..., 'amount':..., 'destination':...}, ...]
    """
    rules = get_split_rules(organization)
    gross = Decimal(str(gross_amount))
    if not rules:
        return [{'name': 'Merchant', 'amount': gross, 'destination': 'merchant'}]

    splits = []
    remaining = gross
    for rule in rules:
        if rule.split_type == 'percentage':
            split_amount = (gross * rule.value / Decimal('100')).quantize(Decimal('0.01'))
        else:
            split_amount = min(rule.value, remaining)

        split_amount = min(split_amount, remaining)
        if split_amount <= 0:
            continue

        dest = rule.destination_account or 'merchant'
        splits.append({
            'name': rule.name,
            'amount': split_amount,
            'destination': dest,
        })
        remaining -= split_amount

    # Remainder goes to merchant
    if remaining > 0:
        splits.append({
            'name': 'Merchant (remainder)',
            'amount': remaining,
            'destination': 'merchant',
        })

    return splits


@db_transaction.atomic
def process_splits(organization, gross_amount, reference_id, description=''):
    """
    Process all splits for a payment.
    Creates ledger entries and queues settlements.
    Returns the list of splits processed.
    """
    from apps.ledger import services as ledger_services
    from apps.settlements.services import queue_payout

    splits = compute_splits(organization, gross_amount)
    results = []

    for split in splits:
        txn = ledger_services.record_payment(
            reference_id=f"{reference_id}_{split['name'][:20]}",
            phone=organization.owner.phone,
            amount=split['amount'],
            name=split['name'],
            provider='split_engine',
            provider_tx_id=reference_id,
            description=f"{description} — {split['name']}",
        )

        # Queue settlement for non-platform destinations
        if split['destination'] != 'platform':
            try:
                payout = queue_payout(
                    merchant_phone=organization.owner.phone,
                    amount=split['amount'],
                    method='intasend',
                    destination=split['destination'],
                )
                split['payout_id'] = str(payout.id) if payout else ''
            except Exception as e:
                logger.warning(f"Split payout failed for {split['name']}: {e}")
                split['payout_id'] = ''

        split['ledger_txn_id'] = str(txn.id) if txn else ''
        results.append(split)

    return results
