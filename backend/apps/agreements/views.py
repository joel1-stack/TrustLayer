import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .services import AgreementService
from .serializers import AgreementSerializer
from .models import Agreement


@csrf_exempt
@require_http_methods(["GET", "POST"])
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
def get_agreement(request, agreement_id):
    agreement = AgreementService.get_agreement(agreement_id)
    if not agreement:
        return JsonResponse({'error': 'Agreement not found'}, status=404)
    serializer = AgreementSerializer(agreement)
    return JsonResponse(serializer.data)
