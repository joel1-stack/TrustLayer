from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .services import TrustScoringService


def _get_merchant(request):
    from apps.merchants.permissions import APIKeyAuthentication
    result = APIKeyAuthentication().authenticate(request)
    return result[0] if result else None


@require_GET
def my_trust_score(request):
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        TrustScoringService.calculate(merchant)
        return JsonResponse({'success': True, 'trust_score': TrustScoringService.details(merchant)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
def public_trust_score(request, merchant_key):
    try:
        from apps.merchants.models import Merchant
        merchant = Merchant.objects.get(merchant_key=merchant_key)
        d = TrustScoringService.details(merchant)
        return JsonResponse({'success': True, 'merchant': merchant.company_name, 'trust_score': {'overall': d['overall'], 'rating': d['rating'], 'total_transactions': d['metrics']['total']}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=404)
