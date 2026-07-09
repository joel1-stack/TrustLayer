from django.shortcuts import render
from django.db.models import Sum, Count, Q
from apps.settlements.models import Settlement
from apps.agreements.models import Agreement


def settlement_view(request):
    status_filter = request.GET.get('status', '')

    qs = Settlement.objects.all().select_related('agreement', 'party')
    if status_filter:
        qs = qs.filter(status=status_filter)

    settlements = qs.order_by('-created_at')[:100]

    queued = Settlement.objects.filter(status='PENDING').count()
    processing = Settlement.objects.filter(status='PROCESSING').count()
    completed = Settlement.objects.filter(status='COMPLETED').count()
    failed = Settlement.objects.filter(status='FAILED').count()
    retrying = Settlement.objects.filter(status='RETRYING').count()

    total_paid = Settlement.objects.filter(status='COMPLETED').aggregate(t=Sum('amount'))['t'] or 0

    recent_failed = Settlement.objects.filter(status='FAILED').order_by('-created_at')[:10]

    return render(request, 'admin_dashboard/settlements.html', {
        'settlements': settlements,
        'queued': queued,
        'processing': processing,
        'completed': completed,
        'failed': failed,
        'retrying': retrying,
        'total_paid': total_paid,
        'recent_failed': recent_failed,
        'current_status': status_filter,
    })
