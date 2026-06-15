"""
JWT Session Views
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from apps.merchants.permissions import APISecretAuthentication
from .services import JWTSessionService


@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
    """POST /api/v1/sessions/create"""
    auth   = APISecretAuthentication()
    result = auth.authenticate(request)
    if not result:
        return JsonResponse({'error': 'Invalid or missing API secret'}, status=401)
    merchant = result[0]

    if not merchant.is_active:
        return JsonResponse({'error': 'Merchant account suspended'}, status=403)

    try:
        data           = json.loads(request.body)
        amount         = data.get('amount')
        description    = data.get('description')
        customer_phone = data.get('customer_phone')

        if not all([amount, description, customer_phone]):
            return JsonResponse({'error': 'amount, description, customer_phone required'}, status=400)

        session = JWTSessionService.create_session(
            merchant=merchant,
            amount=amount,
            description=description,
            customer_phone=customer_phone,
            customer_email=data.get('customer_email', ''),
            success_url=data.get('success_url', ''),
            failure_url=data.get('failure_url', ''),
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # Send SMS to buyer with payment link
        try:
            from apps.notifications.sms import send_sms
            base_url = f"{request.scheme}://{request.get_host()}"
            link = f"{base_url}{session['checkout_url']}"
            send_sms(
                customer_phone,
                f"TrustLayer: Pay KES {amount} for '{description}'. "
                f"Click to pay securely: {link}"
            )
        except Exception:
            pass  # SMS is best-effort

        return JsonResponse({
            'success': True,
            'session': {
                'token':        session['session_token'],
                'short_code':   session['short_code'],
                'checkout_url': session['checkout_url'],
                'expires_at':   session['expires_at'],
                'expires_in':   session['expires_in_seconds'],
            },
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def validate_session(request, token):
    """GET /api/v1/sessions/validate/<token>/ — token can be JWT or short_code"""
    # Resolve short_code to JWT if needed
    resolved = JWTSessionService.resolve_short_code(token)
    if resolved:
        token = resolved
    try:
        result  = JWTSessionService.validate_token(token)
        payload = result['payload']

        # Look up deal linked to this session token
        deal_status = 'PENDING'
        deal_code   = None
        from apps.escrow.models import EscrowDeal
        try:
            deal        = EscrowDeal.objects.get(session_token=token)
            deal_status = deal.status
            deal_code   = deal.deal_code
        except EscrowDeal.DoesNotExist:
            pass

        return JsonResponse({
            'valid': True,
            'session': {
                'merchant_key':   payload.get('merchant_key'),
                'amount':         payload.get('amount'),
                'currency':       payload.get('currency', 'KES'),
                'description':    payload.get('description'),
                'customer_phone': payload.get('customer_phone'),
                'expires_at':     payload.get('exp'),
                'deal_status':    deal_status,
                'deal_code':      deal_code,
            },
        })
    except ValueError as e:
        return JsonResponse({'valid': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def consume_session(request, token):
    """POST /api/v1/sessions/consume/<token>/ — token can be JWT or short_code"""
    resolved = JWTSessionService.resolve_short_code(token)
    if resolved:
        token = resolved
    try:
        JWTSessionService.consume_token(token)
        return JsonResponse({'success': True, 'message': 'Token consumed'})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
