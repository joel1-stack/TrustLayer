import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from apps.auth_decorator import require_api_auth
from .services import ConditionService

@csrf_exempt
@require_http_methods(["POST"])
@require_api_auth
def add_condition(request):
    try:
        data = json.loads(request.body)
        from apps.agreements.models import Agreement
        agreement = Agreement.objects.filter(agreement_id=data['agreement_id']).first()
        if not agreement:
            return JsonResponse({'error': 'Agreement not found'}, status=404)
        condition = ConditionService.add_condition(
            agreement=agreement,
            condition_type=data['condition_type'],
            label=data['label'],
            required=data.get('required', True),
            order=data.get('order', 0),
            timeout_hours=data.get('timeout_hours'),
        )
        return JsonResponse({
            'condition_id': condition.condition_id,
            'agreement_id': agreement.agreement_id,
            'condition_type': condition.condition_type,
            'status': condition.status,
            'label': condition.label,
            'required': condition.required,
        }, status=201)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except KeyError as e:
        return JsonResponse({'error': f'Missing required field: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@require_api_auth
def mark_condition_met(request, condition_id):
    try:
        data = json.loads(request.body) if request.body else {}
        from .models import Condition
        condition = Condition.objects.filter(condition_id=condition_id).first()
        if not condition:
            return JsonResponse({'error': 'Condition not found'}, status=404)
        condition = ConditionService.mark_met(
            condition,
            met_by=data.get('met_by', 'api'),
            evidence=data.get('evidence'),
        )
        from apps.orchestration.services import Orchestrator
        ready = Orchestrator.on_condition_met(condition.agreement, condition)
        return JsonResponse({
            'condition_id': condition.condition_id,
            'status': condition.status,
            'agreement_ready': ready,
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
@require_api_auth
def get_conditions(request, agreement_id):
    from apps.agreements.models import Agreement
    from .models import Condition
    agreement = Agreement.objects.filter(agreement_id=agreement_id).first()
    if not agreement:
        return JsonResponse({'error': 'Agreement not found'}, status=404)
    conditions = Condition.objects.filter(agreement=agreement).values(
        'condition_id', 'condition_type', 'status', 'label', 'required', 'order', 'met_at', 'created_at'
    )
    return JsonResponse(list(conditions), safe=False)