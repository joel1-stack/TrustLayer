import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from apps.merchants.services import MerchantService
from apps.merchants.serializers import MerchantRegisterSerializer


def index(request):
    return render(request, 'portal/index.html')


@csrf_exempt
@require_http_methods(["POST"])
def register_ajax(request):
    try:
        data = json.loads(request.body)
        serializer = MerchantRegisterSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'error': serializer.errors}, status=400)
        v = serializer.validated_data
        result = MerchantService.generate_merchant(
            v['company_name'], v['email'], v['phone'],
            password=v.get('password', ''),
        )
        m = result['merchant']
        creds = result['plaintext_keys']
        return JsonResponse({
            'success': True,
            'merchant': {
                'id': str(m.id),
                'company_name': m.company_name,
                'email': m.email,
                'phone': m.phone,
            },
            'credentials': {
                'merchant_key': creds['merchant_key'],
                'api_key': creds['api_key'],
                'api_secret': creds['api_secret'],
                'webhook_secret': creds['webhook_secret'],
            },
            'redirect': f'/portal/dashboard/?key={creds["api_key"]}&secret={creds["api_secret"]}',
        }, status=201)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_ajax(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        if not email or not password:
            return JsonResponse({'error': 'Email and password required'}, status=400)

        from apps.merchants.models import Merchant
        try:
            merchant = Merchant.objects.get(email=email, is_active=True)
        except Merchant.DoesNotExist:
            return JsonResponse({'error': 'Invalid email or password'}, status=401)

        if not merchant.check_password(password):
            return JsonResponse({'error': 'Invalid email or password'}, status=401)

        return JsonResponse({
            'success': True,
            'merchant': {
                'id': str(merchant.id),
                'company_name': merchant.company_name,
                'email': merchant.email,
                'phone': merchant.phone,
            },
            'redirect': '/portal/dashboard/',
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
