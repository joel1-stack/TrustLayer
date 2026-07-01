"""
Settlement Views — Queue and process payouts.
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from . import services
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def queue_payout_view(request):
    try:
        data = json.loads(request.body)
        phone = data.get('phone', '').strip()
        amount = data.get('amount')
        method = data.get('method', 'intasend')
        if not phone or not amount:
            return JsonResponse({'error': 'phone and amount required'}, status=400)
        payout = services.queue_payout(phone, amount, method)
        return JsonResponse({'success': True, 'payout_id': str(payout.id), 'status': payout.status})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def process_payout_view(request):
    try:
        data = json.loads(request.body)
        payout_id = data.get('payout_id', '')
        if not payout_id:
            return JsonResponse({'error': 'payout_id required'}, status=400)
        result = services.process_payout(payout_id)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
