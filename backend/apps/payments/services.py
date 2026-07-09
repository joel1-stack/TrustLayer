from decimal import Decimal
from .models import PaymentTransaction
from .adapters.registry import get_adapter

class PaymentService:

    @staticmethod
    def generate_payment_link(agreement, phone='', provider='intasend'):
        """Generate a payment link for an agreement using the given provider."""
        adapter = get_adapter(provider)
        reference = agreement.agreement_id
        result = adapter.generate_link(amount=agreement.amount, phone=phone, reference=reference)

        tx = PaymentTransaction.objects.create(
            agreement=agreement,
            provider=provider,
            amount=agreement.amount,
            currency=agreement.currency,
            phone=phone,
            payment_url=result.get('payment_url', ''),
            reference=reference,
            status='pending' if result.get('success') else 'failed',
            provider_tx_id=result.get('provider_reference', ''),
            raw_response=result,
        )

        return tx, result

    @staticmethod
    def process_webhook(provider, raw_payload):
        """Process incoming webhook: convert to standard format, update agreement."""
        adapter = get_adapter(provider)
        standard = adapter.handle_webhook(raw_payload)

        from apps.agreements.models import Agreement
        agreement = Agreement.objects.filter(agreement_id=standard['internal_reference']).first()
        if not agreement:
            return standard, None

        # Update payment transaction
        tx = PaymentTransaction.objects.filter(
            agreement=agreement,
            provider=provider,
            reference=standard['internal_reference'],
        ).last()

        if tx:
            tx.status = standard['status']
            tx.provider_tx_id = standard['provider_transaction_id']
            tx.raw_response = standard['raw_payload']
            if standard['status'] == 'completed':
                tx.completed_at = __import__('django.utils.timezone', fromlist=['timezone']).timezone.now()
            tx.save()

        return standard, agreement