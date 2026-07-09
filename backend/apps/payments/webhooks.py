"""
Payment Provider Webhook Receiver.

Direction 2: Payment Provider → TrustLayer (Incoming)
IntaSend/M-Pesa/Stripe POST here when a payment or payout completes.

Always return 200 immediately. Process in background.
"""
import json
import logging
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import WebhookEvent
from .services import PaymentService
from apps.orchestration.services import Orchestrator

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def intasend_webhook(request):
    """POST /webhooks/intasend/ — IntaSend sends payment/payout updates here."""
    return _handle_webhook(request, 'intasend')


@csrf_exempt
@require_http_methods(["POST"])
def mpesa_webhook(request):
    """POST /webhooks/mpesa/ — Safaricom sends STK Push / B2C callbacks here."""
    return _handle_webhook(request, 'mpesa')


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """POST /webhooks/stripe/ — Stripe sends payment intents / payouts here."""
    return _handle_webhook(request, 'stripe')


def _handle_webhook(request, provider):
    """Universal webhook handler."""
    try:
        raw_body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = WebhookEvent.objects.create(
        provider=provider,
        raw_body=raw_body,
    )
    event.save()

    try:
        standard, agreement = PaymentService.process_webhook(provider, raw_body)
        event.provider_event_id = standard.get('provider_transaction_id', '')
        event.signature_valid = True

        # If we found the agreement and payment is completed, orchestrate
        if agreement and standard['status'] == 'completed':
            try:
                Orchestrator.on_payment_collected(
                    agreement=agreement,
                    amount=standard['amount'],
                    reference=standard['provider_transaction_id'],
                    phone=standard.get('phone', ''),
                )
            except Exception as e:
                logger.error(f"Orchestration failed for {agreement.agreement_id}: {e}")
                event.error = f"Orchestration error: {e}"

        event.processed = True
        event.processed_at = __import__('django.utils.timezone', fromlist=['timezone']).timezone.now()
        event.save()

    except Exception as e:
        logger.error(f"Webhook processing failed for {provider}: {e}")
        event.error = str(e)
        event.save()

    # Always return 200
    return JsonResponse({'status': 'received'})