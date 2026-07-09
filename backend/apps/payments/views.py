import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .services import PaymentService
from apps.orchestration.services import Orchestrator


@csrf_exempt
@require_http_methods(["POST"])
def generate_payment_link(request):
    """
    POST /api/payments/link/
    
    Generate a payment link for an agreement using the specified provider.
    
    Body:
        agreement_id: str (required)
        phone: str (optional, for STK push)
        provider: str (optional, default 'intasend')
    
    Returns:
        payment_url: str
        transaction_id: str
        provider: str
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    agreement_id = data.get('agreement_id', '').strip()
    phone = data.get('phone', '').strip()
    provider = data.get('provider', 'intasend').strip()

    if not agreement_id:
        return JsonResponse({'error': 'agreement_id is required'}, status=400)

    from apps.agreements.models import Agreement
    agreement = Agreement.objects.filter(agreement_id=agreement_id).first()
    if not agreement:
        return JsonResponse({'error': 'Agreement not found'}, status=404)

    # Generate payment link via adapter
    tx, result = PaymentService.generate_payment_link(agreement, phone=phone, provider=provider)

    if not result.get('success'):
        return JsonResponse({'error': result.get('error', 'Failed to generate link')}, status=502)

    # Save payment URL on agreement
    agreement.payment_url = result.get('payment_url', '')
    agreement.save(update_fields=['payment_url', 'updated_at'])

    # Orchestrate: move to PAYMENT_PENDING
    Orchestrator.on_payment_link_generated(agreement, payment_url=result.get('payment_url', ''))

    return JsonResponse({
        'payment_url': result.get('payment_url', ''),
        'transaction_id': tx.transaction_id,
        'provider': provider,
        'agreement_id': agreement.agreement_id,
        'status': 'PAYMENT_PENDING',
    })