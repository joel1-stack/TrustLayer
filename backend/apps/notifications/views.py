from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.auth_decorator import require_api_auth
from .models import NotificationEvent

@require_http_methods(["GET"])
@require_api_auth
def list_notifications(request, agreement_id):
    from apps.agreements.models import Agreement
    agreement = Agreement.objects.filter(agreement_id=agreement_id).first()
    if not agreement:
        return JsonResponse({'error': 'Agreement not found'}, status=404)
    notifications = NotificationEvent.objects.filter(agreement=agreement).values(
        'event_id', 'event', 'channel', 'message', 'sent', 'sent_at', 'created_at'
    )
    return JsonResponse(list(notifications), safe=False)