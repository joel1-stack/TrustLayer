"""
Ledger Views — Dashboard stats, wallet info.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from . import services
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def dashboard_stats(request):
    merchant_phone = request.GET.get('phone', '')
    try:
        stats = services.get_dashboard_stats(merchant_phone)
        return JsonResponse({'success': True, 'data': stats})
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def wallet_balance(request, phone):
    try:
        wallet = services.get_or_create_wallet(phone)
        return JsonResponse({
            'success': True,
            'phone': phone,
            'balance': float(wallet.balance),
            'owner_type': wallet.owner_type,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
