from datetime import timedelta
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count
from ..models import LoginAttempt, AuditLogEntry


def security_view(request):
    today = timezone.now().date()

    failed_logins = LoginAttempt.objects.filter(success=False).count()
    failed_today = LoginAttempt.objects.filter(success=False, timestamp__date=today).count()
    successful_logins = LoginAttempt.objects.filter(success=True).count()
    unique_ips = LoginAttempt.objects.values('ip_address').distinct().count()
    blocked_ips_today = LoginAttempt.objects.filter(
        success=False, timestamp__gte=timezone.now() - timedelta(minutes=15)
    ).values('ip_address').annotate(attempts=Count('id')).filter(attempts__gte=5).count()

    recent_attempts = LoginAttempt.objects.order_by('-timestamp')[:50]

    audit_events = AuditLogEntry.objects.order_by('-timestamp')[:50]

    return render(request, 'admin_dashboard/security.html', {
        'failed_logins': failed_logins,
        'failed_today': failed_today,
        'successful_logins': successful_logins,
        'unique_ips': unique_ips,
        'blocked_ips_today': blocked_ips_today,
        'recent_attempts': recent_attempts,
        'audit_events': audit_events,
    })
