"""
Escrow Services — Deal creation, state transitions, fee calculation.
"""
import uuid
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from apps.merchants.models import Merchant
from .models import EscrowDeal


class EscrowService:

    FEE_PERCENTAGE = 1.5  # 1.5% per transaction

    @classmethod
    def create_deal(cls, merchant: Merchant, amount: float, description: str,
                    buyer_phone: str, buyer_email: str = '', session_token: str = '') -> EscrowDeal:
        deal_code = f"TL-{uuid.uuid4().hex[:6].upper()}"
        fee       = round((float(amount) * cls.FEE_PERCENTAGE) / 100, 2)

        return EscrowDeal.objects.create(
            merchant=merchant,
            deal_code=deal_code,
            session_token=session_token,
            amount=amount,
            fee_amount=fee,
            description=description,
            buyer_phone=buyer_phone,
            buyer_email=buyer_email,
            status='PENDING',
        )

    @classmethod
    @transaction.atomic
    def confirm_payment(cls, deal_code: str, mpesa_receipt: str,
                        payment_tx=None) -> EscrowDeal:
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status != 'PENDING':
            raise ValueError(f"Deal is {deal.status}, expected PENDING")
        if payment_tx:
            deal.payment_transaction = payment_tx
        deal.mpesa_receipt  = mpesa_receipt
        deal.status         = 'HELD'
        deal.auto_release_at = timezone.now() + timedelta(hours=48)
        deal.save()
        return deal

    @classmethod
    @transaction.atomic
    def buyer_confirm_delivery(cls, deal_code: str) -> EscrowDeal:
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status != 'HELD':
            raise ValueError(f"Deal is {deal.status}, expected HELD")
        deal.buyer_confirmed    = True
        deal.buyer_confirmed_at = timezone.now()
        if deal.seller_confirmed:
            deal.status      = 'RELEASED'
            deal.released_at = timezone.now()
        deal.save()
        return deal

    @classmethod
    @transaction.atomic
    def seller_confirm_delivery(cls, deal_code: str) -> EscrowDeal:
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status != 'HELD':
            raise ValueError(f"Deal is {deal.status}, expected HELD")
        deal.seller_confirmed    = True
        deal.seller_confirmed_at = timezone.now()
        if deal.buyer_confirmed:
            deal.status      = 'RELEASED'
            deal.released_at = timezone.now()
        deal.save()
        return deal

    @classmethod
    @transaction.atomic
    def refund(cls, deal_code: str) -> EscrowDeal:
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status not in ['HELD', 'PENDING']:
            raise ValueError(f"Cannot refund deal in {deal.status} status")
        deal.status      = 'REFUNDED'
        deal.released_at = timezone.now()
        deal.save()
        return deal

    @classmethod
    @transaction.atomic
    def open_dispute(cls, deal_code: str, reason: str) -> EscrowDeal:
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status != 'HELD':
            raise ValueError(f"Cannot dispute deal in {deal.status} status")
        deal.status         = 'DISPUTED'
        deal.disputed_at    = timezone.now()
        deal.dispute_reason = reason
        deal.save()
        return deal

    @classmethod
    @transaction.atomic
    def resolve_dispute(cls, deal_code: str, winner: str) -> EscrowDeal:
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status != 'DISPUTED':
            raise ValueError(f"Deal is {deal.status}, expected DISPUTED")
        if winner == 'buyer':
            deal.status = 'REFUNDED'
        elif winner == 'seller':
            deal.status = 'RELEASED'
        else:
            raise ValueError("winner must be 'buyer' or 'seller'")
        deal.released_at = timezone.now()
        deal.save()
        return deal
 