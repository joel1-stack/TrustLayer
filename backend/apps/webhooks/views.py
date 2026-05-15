import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from .models import WebhookEndpoint, WebhookDelivery
from .services import WebhookService


def _get_merchant(request):
    from apps.merchants.permissions import APIKeyAuthentication
    result = APIKeyAuthentication().authenticate(request)
    return result[0] if result else None


@csrf_exempt
@require_POST
def register_webhook(request):
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        data = json.loads(request.body)
        url  = data.get('url')
        if not url:
            return JsonResponse({'success': False, 'error': 'URL required'}, status=400)
        result = WebhookService.create_endpoint(merchant, url, data.get('events', ['all']), data.get('description', ''))
        return JsonResponse({'success': True, 'webhook': result})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
def list_webhooks(request):
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    endpoints = WebhookEndpoint.objects.filter(merchant=merchant, is_active=True)
    return JsonResponse({'success': True, 'webhooks': [
        {'id': str(e.id), 'url': e.url, 'events': e.events, 'description': e.description, 'created_at': e.created_at.isoformat()}
        for e in endpoints
    ]})


@csrf_exempt
@require_POST
def delete_webhook(request, webhook_id):
    merchant = _get_merchant(request)
    if not merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        ep = WebhookEndpoint.objects.get(id=webhook_id, merchant=merchant)
        ep.is_active = False
        ep.save()
        return JsonResponse({'success': True, 'message': 'Webhook deleted'})
    except WebhookEndpoint.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)


@require_GET
def delivery_logs(request, webhook_id):
    deliveries = WebhookDelivery.objects.filter(endpoint_id=webhook_id).order_by('-created_at')[:50]
    return JsonResponse({'success': True, 'deliveries': [
        {'id': str(d.id), 'event_type': d.event_type, 'status': d.status,
         'http_status': d.http_status, 'attempt_count': d.attempt_count,
         'created_at': d.created_at.isoformat(), 'error': d.error_message[:200]}
        for d in deliveries
    ]})
