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
from django.utils import timezone
from .models import WebhookEvent, PaymentTransaction
from .services import PaymentService
from apps.orchestration.services import Orchestrator
from apps.state_machine.services import StateMachine
from apps.notifications.services import NotificationService
from apps.ledger.models import LedgerEntry

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
    # Parse JSON
    try:
        raw_body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Get provider-specific signature header
    signature = None
    if provider == 'intasend':
        signature = request.META.get('HTTP_X_INTASEND_SIGNATURE', '')
    elif provider == 'stripe':
        signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    
    # Create webhook event record (but don't save yet - we'll save after verification)
    event = WebhookEvent(
        provider=provider,
        raw_body=raw_body,
    )
    
    ip_address = request.META.get('REMOTE_ADDR')
    
    try:
        # Verify signature
        adapter = get_adapter(provider)
        if signature and hasattr(adapter, 'verify_webhook_signature'):
            if not adapter.verify_webhook_signature(raw_body, signature):
                logger.warning(f"Invalid webhook signature for {provider}")
                event.signature_valid = False
                event.error = 'Invalid signature'
                event.save()
                return JsonResponse({'status': 'received'}, status=200)  # Still return 200 to avoid retries
        
        event.signature_valid = True
        
        # Process webhook through adapter
        standard, agreement = PaymentService.process_webhook(provider, raw_body)
        event.provider_event_id = standard.get('provider_transaction_id', '')
        
        if agreement:
            provider_status = standard['status']
            amount = standard['amount']
            reference = standard['provider_transaction_id']
            phone = standard.get('phone', '')
            
            # DUPLICATE SHIELD: Check if we already processed this provider_ref
            from .models import PaymentTransaction
            existing_tx = PaymentTransaction.objects.filter(
                provider=provider,
                provider_tx_id=reference,
                status__in=['completed', 'pending'],
            ).first()
            
            if existing_tx:
                logger.info(f"Duplicate webhook detected for {provider}:{reference}, skipping")
                event.processed = True
                event.processed_at = timezone.now()
                event.save()
                return JsonResponse({'status': 'received'}, status=200)
            
            # State machine transitions based on provider status
            # Only process if agreement is in expected state
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
                # Full flow: SUBMITTED/PENDING → PENDING → AVAILABLE → HELD
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
            
            elif provider_status == 'cancelled':
                if agreement.status in ('SUBMITTED', 'PENDING'):
                    try:
                        StateMachine.transition(
                            agreement, 'CANCELLED',
                            triggered_by='provider_webhook',
                            actor_id=provider,
                            actor_role='provider_webhook',
                            channel='webhook',
                            ip_address=ip_address,
                            provider_ref=reference,
                            trigger_reason='payment_cancelled',
                            reason=f'Customer cancelled payment on provider page',
                            evidence={'provider': provider, 'provider_ref': reference}
                        )
                    except Exception as e:
                        logger.error(f"Cancelled transition failed for {agreement.agreement_id}: {e}")
        
        event.processed = True
        event.processed_at = timezone.now()
        event.save()
    
    except Exception as e:
        logger.error(f"Webhook processing failed for {provider}: {e}")
        event.error = str(e)
        event.save()
    
    # Always return 200 immediately
    return JsonResponse({'status': 'received'})
