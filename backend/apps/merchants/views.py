"""
Merchant API Views
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .services import MerchantService
from .permissions import APIKeyAuthentication, APISecretAuthentication
from .serializers import MerchantRegisterSerializer, MerchantResponseSerializer


@csrf_exempt
@require_http_methods(["POST"])
def register_merchant(request):
    """POST /api/v1/merchants/register"""
    try:
        data       = json.loads(request.body)
        serializer = MerchantRegisterSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'error': serializer.errors}, status=400)

        v      = serializer.validated_data
        result = MerchantService.generate_merchant(v['company_name'], v['email'], v['phone'])
        m      = result['merchant']

        return JsonResponse({
            'success': True,
            'message': 'Merchant created. SAVE THESE KEYS — they will never be shown again.',
            'merchant': {
                'id':           str(m.id),
                'company_name': m.company_name,
                'email':        m.email,
                'phone':        m.phone,
            },
            'credentials': {
                'merchant_key':   result['plaintext_keys']['merchant_key'],
                'api_key':        result['plaintext_keys']['api_key'],
                'api_secret':     result['plaintext_keys']['api_secret'],
                'webhook_secret': result['plaintext_keys']['webhook_secret'],
            },
            'warning': result['warning'],
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_merchant(request):
    """POST /api/v1/merchants/login"""
    try:
        data    = json.loads(request.body)
        api_key = data.get('api_key', '')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    merchant = MerchantService.authenticate_api_key(api_key)
    if not merchant:
        return JsonResponse({'error': 'Invalid API key'}, status=401)

    return JsonResponse({'success': True, 'merchant': MerchantResponseSerializer(merchant).data})


@csrf_exempt
@require_http_methods(["GET"])
def merchant_profile(request):
    """GET /api/v1/merchants/profile"""
    auth     = APIKeyAuthentication()
    result   = auth.authenticate(request)
    if not result:
        return JsonResponse({'error': 'Invalid or missing API key'}, status=401)
    merchant = result[0]
    return JsonResponse({'success': True, 'merchant': MerchantResponseSerializer(merchant).data})


@csrf_exempt
@require_http_methods(["POST"])
def regenerate_keys(request):
    """POST /api/v1/merchants/keys/regenerate"""
    auth   = APISecretAuthentication()
    result = auth.authenticate(request)
    if not result:
        return JsonResponse({'error': 'Invalid or missing API secret'}, status=401)
    merchant = result[0]

    try:
        new_keys = MerchantService.rotate_keys(merchant)
        return JsonResponse({
            'success': True,
            'message': 'Keys rotated. Old keys valid 24h.',
            'credentials': {
                'api_key':    new_keys['api_key'],
                'api_secret': new_keys['api_secret'],
            },
            'version':           new_keys['version'],
            'grace_period_ends': str(new_keys['grace_period_ends']),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
