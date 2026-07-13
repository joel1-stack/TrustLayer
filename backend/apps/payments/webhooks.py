"""
Payment Provider Webhook Receiver.

Direction 2: Payment Provider -> TrustLayer (Incoming)
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
from apps.state_machine.services import StateMachine
from apps.notifications.services import NotificationService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def intasend_webhook(request):
    return _handle_webhook(request, 'intasend')


@csrf_exempt
@require_http_methods(["POST"])
def mpesa_webhook(request):
    return _handle_webhook(request, 'mpesa')


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    return _handle_webhook(request, 'stripe')


def _handle_webhook(request, provider):
    try:
        raw_body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = WebhookEvent.objects.create(
        provider=provider,
        raw_body=raw_body,
    )
    event.save()

    ip_address = request.META.get('REMOTE_ADDR')

    try:
        standard, agreement = PaymentService.process_webhook(provider, raw_body)
        event.provider_event_id = standard.get('provider_transaction_id', '')
        event.signature_valid = True

        if agreement:
            provider_status = standard['status']
            amount = standard['amount']
            reference = standard['provider_transaction_id']
            phone = standard.get('phone', '')

            if provider_status == 'pending':
                if agreement.status == 'SUBMITTED':
                    try:
                        StateMachine.transition(
                            agreement, 'PENDING',
                            triggered_by='provider_webhook',
                            actor_id=provider,
                            actor_role='provider_webhook',
                            channel='webhook',
                            ip_address=ip_address,
                            provider_ref=reference,
                            trigger_reason='payment_pending',
                            reason=f'Provider acknowledged payment (ref: {reference})',
                            evidence={'provider': provider, 'provider_ref': reference}
                        )
                        NotificationService.on_payment_pending(agreement)
                    except Exception as e:
                        logger.error(f"Pending transition failed for {agreement.agreement_id}: {e}")

            elif provider_status == 'completed':
                try:
                    Orchestrator.on_payment_collected(
                        agreement=agreement,
                        amount=Decimal(str(amount)),
                        reference=reference,
                        phone=phone,
                        ip_address=ip_address,
                    )
                except Exception as e:
                    logger.error(f"Orchestration failed for {agreement.agreement_id}: {e}")
                    event.error = f"Orchestration error: {e}"

            elif provider_status == 'failed':
                if agreement.status in ('SUBMITTED', 'PENDING'):
                    try:
                        StateMachine.transition(
                            agreement, 'DECLINED',
                            triggered_by='provider_webhook',
                            actor_id=provider,
                            actor_role='provider_webhook',
                            channel='webhook',
                            ip_address=ip_address,
                            provider_ref=reference,
                            trigger_reason='payment_declined',
                            reason=f'Provider declined payment: {standard.get("failure_reason", "Unknown reason")}',
                            evidence={'provider': provider, 'provider_ref': reference}
                        )
                        NotificationService.on_payment_declined(agreement, reason=standard.get('failure_reason', ''))
                    except Exception as e:
                        logger.error(f"Declined transition failed for {agreement.agreement_id}: {e}")

        event.processed = True
        event.processed_at = __import__('django.utils.timezone', fromlist=['timezone']).timezone.now()
        event.save()

    except Exception as e:
        logger.error(f"Webhook processing failed for {provider}: {e}")
        event.error = str(e)
        event.save()

    return JsonResponse({'status': 'received'})
