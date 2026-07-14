import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from apps.auth_decorator import require_api_auth
from .services import AgreementService
from .serializers import AgreementSerializer
from .models import Agreement


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_api_auth
def list_or_create_agreement(request):
    if request.method == 'GET':
        agreements = Agreement.objects.all().order_by('-created_at')
        data = [AgreementSerializer(a).data for a in agreements]
        return JsonResponse({'count': len(data), 'results': data})
    try:
        data = json.loads(request.body)
        agreement = AgreementService.create_agreement(
            title=data.get('title', ''),
            amount=data['amount'],
            creator_id=data['creator_id'],
            description=data.get('description', ''),
            currency=data.get('currency', 'KES'),
            creator_type=data.get('creator_type', 'organization'),
            metadata=data.get('metadata'),
        )
        for party in data.get('parties', []):
            AgreementService.add_party(
                agreement=agreement,
                role=party['role'],
                identifier=party['identifier'],
                name=party['name'],
                split_percentage=party.get('split_percentage'),
                split_fixed=party.get('split_fixed'),
                payout_method=party.get('payout_method', ''),
                payout_details=party.get('payout_details'),
            )
        serializer = AgreementSerializer(agreement)
        return JsonResponse(serializer.data, status=201)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except KeyError as e:
        return JsonResponse({'error': f'Missing required field: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@require_api_auth
def get_agreement(request, agreement_id):
    agreement = AgreementService.get_agreement(agreement_id)
    if not agreement:
        return JsonResponse({'error': 'Agreement not found'}, status=404)
    serializer = AgreementSerializer(agreement)
    return JsonResponse(serializer.data)


@csrf_exempt
@require_http_methods(["POST"])
@require_api_auth
def approve_kyc(request, agreement_id):
    try:
        data = json.loads(request.body) if request.body else {}
        from apps.state_machine.services import StateMachine
        from apps.orchestration.services import Orchestrator
        agreement = AgreementService.get_agreement(agreement_id)
        if not agreement:
            return JsonResponse({'error': 'Agreement not found'}, status=404)
        if agreement.status != 'PENDING_KYC':
            return JsonResponse({'error': f'Agreement is {agreement.status}, not PENDING_KYC'}, status=400)
        kyc_data = data.get('kyc', {})
        meta = agreement.metadata or {}
        meta['kyc'] = {**meta.get('kyc', {}), **kyc_data, 'approved': True, 'approved_by': data.get('approved_by', 'system')}
        agreement.metadata = meta
        agreement.save(update_fields=['metadata'])
        ip_address = request.META.get('REMOTE_ADDR')
        StateMachine.transition(
            agreement, 'CONFIRMED',
            triggered_by=data.get('approved_by', 'system'),
            actor_id=data.get('actor_id', ''),
            actor_role='admin',
            channel='api',
            ip_address=ip_address,
            trigger_reason='kyc_approved',
            reason=f'KYC approved for tier {StateMachine.get_required_kyc_tier(agreement.amount)}',
            evidence={'kyc': kyc_data}
        )
        from apps.notifications.services import NotificationService
        NotificationService.on_kyc_approved(agreement)
        return JsonResponse({'status': 'kyc_approved', 'agreement_id': agreement.agreement_id, 'status_code': agreement.status_code})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_api_auth
def reject_kyc(request, agreement_id):
    try:
        data = json.loads(request.body) if request.body else {}
        from apps.state_machine.services import StateMachine
        agreement = AgreementService.get_agreement(agreement_id)
        if not agreement:
            return JsonResponse({'error': 'Agreement not found'}, status=404)
        if agreement.status != 'PENDING_KYC':
            return JsonResponse({'error': f'Agreement is {agreement.status}, not PENDING_KYC'}, status=400)
        ip_address = request.META.get('REMOTE_ADDR')
        StateMachine.transition(
            agreement, 'REJECTED',
            triggered_by=data.get('rejected_by', 'system'),
            actor_role='admin',
            channel='api',
            ip_address=ip_address,
            trigger_reason='kyc_rejected',
            reason=data.get('reason', 'KYC verification rejected'),
        )
        return JsonResponse({'status': 'kyc_rejected', 'agreement_id': agreement.agreement_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
