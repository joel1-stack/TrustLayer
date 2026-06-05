"""
Escrow Services — Deal creation, state transitions, fee calculation, B2C release.
"""
import uuid
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from apps.merchants.models import Merchant
from .models import EscrowDeal, FeeRecord
import logging

logger = logging.getLogger(__name__)


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
        deal.mpesa_receipt   = mpesa_receipt
        deal.status          = 'HELD'
        deal.ledger_status   = 'HELD'
        deal.amount_paid     = deal.amount
        deal.auto_release_at = timezone.now() + timedelta(hours=48)
        deal.save()
        return deal

    @classmethod
    @transaction.atomic
    def buyer_confirm_delivery(cls, deal_code: str) -> EscrowDeal:
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status not in ('HELD', 'DELIVERED'):
            raise ValueError(f"Deal is {deal.status}, expected HELD or DELIVERED")
        deal.buyer_confirmed    = True
        deal.buyer_confirmed_at = timezone.now()

        if deal.status == 'DELIVERED' or deal.seller_confirmed:
            deal.status = 'RELEASED'

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
            deal.status = 'RELEASED'
        deal.save()
        return deal

    @classmethod
    @transaction.atomic
    def release_funds(cls, deal_code: str) -> dict:
        """
        Trigger B2C transfer from TrustLayer's paybill to the merchant's phone.
        Called when a deal transitions DELIVERED/HELD → RELEASED.
        """
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status not in ('DELIVERED', 'HELD', 'RELEASED'):
            raise ValueError(f"Deal is {deal.status}, cannot release funds")

        if deal.ledger_status in ('RELEASE_PENDING', 'RELEASED'):
            return {'success': True, 'message': 'Funds already being released'}

        if deal.ledger_status == 'STUCK':
            return {'success': False, 'error': 'Funds stuck — admin intervention required'}

        # Calculate net amount after fee
        net_amount = deal.amount - deal.fee_amount

        # Initiate B2C transfer to merchant's phone
        from apps.payments.adapters.mpesa import mpesa
        result = mpesa.b2c_transfer(
            phone=deal.merchant.phone,
            amount=int(net_amount),
            occasion=deal.deal_code,
            remarks=f"TrustLayer release {deal.deal_code}",
        )

        if result.get('success'):
            deal.ledger_status = 'RELEASE_PENDING'
            deal.b2c_conversation_id = result.get('conversation_id', '')
            deal.amount_released = net_amount
            deal.fee_charged = deal.fee_amount
            deal.save()

            FeeRecord.objects.create(
                deal=deal,
                amount=deal.fee_amount,
                rate=Decimal(str(cls.FEE_PERCENTAGE)),
            )

            logger.info(f"B2C initiated for {deal_code}: conv={result.get('conversation_id')}, net={net_amount}")
            return {
                'success': True,
                'message': 'B2C transfer initiated',
                'conversation_id': result.get('conversation_id'),
                'net_amount': str(net_amount),
                'fee': str(deal.fee_amount),
            }
        else:
            deal.ledger_status = 'STUCK'
            deal.b2c_failure_reason = result.get('error', 'B2C API call failed')
            deal.save()

            logger.error(f"B2C failed for {deal_code}: {result.get('error')}")
            return {
                'success': False,
                'error': result.get('error', 'B2C transfer failed'),
            }

    @classmethod
    @transaction.atomic
    def refund(cls, deal_code: str) -> EscrowDeal:
        deal = EscrowDeal.objects.select_for_update().get(deal_code=deal_code)
        if deal.status not in ['HELD', 'PENDING']:
            raise ValueError(f"Cannot refund deal in {deal.status} status")
        deal.status        = 'REFUNDED'
        deal.ledger_status = 'RELEASED'
        deal.released_at   = timezone.now()
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
            deal.status        = 'REFUNDED'
            deal.ledger_status = 'RELEASED'
        elif winner == 'seller':
            deal.status = 'RELEASED'
        else:
            raise ValueError("winner must be 'buyer' or 'seller'")
        deal.released_at = timezone.now()
        deal.save()
        return deal
