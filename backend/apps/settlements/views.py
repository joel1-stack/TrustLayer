from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from apps.auth_decorator import require_api_auth
from .services import SettlementService
from .models import Settlement

@require_http_methods(["GET"])
@require_api_auth
def list_settlements(request, agreement_id):
    from apps.agreements.models import Agreement
    agreement = Agreement.objects.filter(agreement_id=agreement_id).first()
    if not agreement:
        return JsonResponse({'error': 'Agreement not found'}, status=404)
    settlements = Settlement.objects.filter(agreement=agreement).values(
        'settlement_id', 'party__name', 'amount', 'currency', 'provider', 'status',
        'provider_tx_id', 'retry_count', 'created_at', 'completed_at'
    )
    return JsonResponse(list(settlements), safe=False)

@csrf_exempt
@require_http_methods(["POST"])
@require_api_auth
def trigger_settlement(request, agreement_id):
    from apps.agreements.models import Agreement
    from apps.orchestration.services import Orchestrator
    agreement = Agreement.objects.filter(agreement_id=agreement_id).first()
    if not agreement:
        return JsonResponse({'error': 'Agreement not found'}, status=404)
    try:
        settlements = Orchestrator.trigger_settlement(agreement)
        return JsonResponse({
            'status': 'settled',
            'settlements': [{'id': s.settlement_id, 'amount': str(s.amount), 'party': s.party.name, 'status': s.status} for s in settlements],
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)