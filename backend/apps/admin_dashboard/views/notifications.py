from django.shortcuts import render
from django.db.models import Count
from apps.notifications.models import NotificationEvent


def notifications_view(request):
    status_filter = request.GET.get('status', '')

    qs = NotificationEvent.objects.all().select_related('agreement')
    if status_filter == 'sent':
        qs = qs.filter(sent=True)
    elif status_filter == 'failed':
        qs = qs.filter(error__gt='')
    elif status_filter == 'pending':
        qs = qs.filter(sent=False, error='')

    events = qs.order_by('-created_at')[:100]

    sent_count = NotificationEvent.objects.filter(sent=True).count()
    failed_count = NotificationEvent.objects.filter(error__gt='').count()
    pending_count = NotificationEvent.objects.filter(sent=False, error='').count()

    by_type = NotificationEvent.objects.values('event').annotate(c=Count('id')).order_by('-c')

    return render(request, 'admin_dashboard/notifications.html', {
        'events': events,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'pending_count': pending_count,
        'by_type': by_type,
        'current_status': status_filter,
    })
