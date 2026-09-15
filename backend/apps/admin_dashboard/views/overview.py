from datetime import timedelta
from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from apps.agreements.models import Case as Agreement
from apps.payments.models import WebhookEvent
from ..models import LoginAttempt, AuditLogEntry


def dashboard(request):
    today = timezone.now().date()

    # ── Active incidents ──────────────────────────────────────────────────────
    # Cases that are open / in-progress (not yet in a terminal state)
    active_cases = Agreement.objects.filter(
        status_code_value__gte=10000,
        status_code_value__lte=17999,
    ).exclude(
        status_code_value__in=[22000, 23000, 21000]
    ).count()

    # Cases currently in a diagnosing / waiting state
    waiting_count = Agreement.objects.filter(
        status_code_value__in=[10500, 12000, 13000]
    ).count()

    # Cases escalated / disputed
    disputed_count = Agreement.objects.filter(
        status_code_value=15500
    ).count()

    # ── Mean Time To Resolution (MTTR) ────────────────────────────────────────
    # Resolved cases: status 18000 (SETTLED/RESOLVED) or 21000 (CANCELLED)
    resolved_qs = Agreement.objects.filter(
        status_code_value__in=[18000, 21000]
    ).exclude(updated_at=None)

    total_resolved = resolved_qs.count()

    if total_resolved > 0:
        total_seconds = 0
        for case in resolved_qs.only('created_at', 'updated_at'):
            delta = case.updated_at - case.created_at
            total_seconds += max(delta.total_seconds(), 0)
        avg_seconds = total_seconds / total_resolved
        minutes, secs = divmod(int(avg_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            avg_mttr = f"{hours}h {minutes}m"
        elif minutes > 0:
            avg_mttr = f"{minutes}m {secs:02d}s"
        else:
            avg_mttr = f"{secs}s"
    else:
        avg_mttr = "—"

    # ── Auto-resolved rate ────────────────────────────────────────────────────
    # Cases resolved today
    auto_resolved_today = Agreement.objects.filter(
        status_code_value=18000,
        updated_at__date=today,
    ).count()

    total_closed_today = Agreement.objects.filter(
        status_code_value__in=[18000, 21000, 24000, 26000],
        updated_at__date=today,
    ).count()

    if total_closed_today > 0:
        rate = round((auto_resolved_today / total_closed_today) * 100)
        auto_resolved_rate = f"{rate}%"
    else:
        auto_resolved_rate = "—"

    # ── Engine status ─────────────────────────────────────────────────────────
    engine_status = {
        'context':      'running',
        'diagnosis':    'running',
        'policy':       'running',
        'action':       'running',
        'verification': 'running',
        'notification': 'running',
    }

    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_status = 'connected'
    except Exception:
        db_status = 'error'

    try:
        from django.conf import settings
        import redis
        r = redis.from_url(getattr(settings, 'REDIS_URL', 'redis://localhost:6379'))
        r.ping()
        redis_status = 'connected'
    except Exception:
        redis_status = 'error'

    # ── Recent errors ─────────────────────────────────────────────────────────
    recent_errors = WebhookEvent.objects.filter(
        error__isnull=False
    ).order_by('-created_at')[:5]

    # ── Security ──────────────────────────────────────────────────────────────
    failed_logins = LoginAttempt.objects.filter(
        success=False, timestamp__date=today
    ).count()

    # ── Visitor / page-view tracking ──────────────────────────────────────────
    total_page_views = AuditLogEntry.objects.filter(action='viewed_page').count()
    unique_visitors = AuditLogEntry.objects.filter(
        action='viewed_page'
    ).values('actor_ip').distinct().count()
    total_views_today = AuditLogEntry.objects.filter(
        action='viewed_page', timestamp__date=today
    ).count()

    growth_days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        views = AuditLogEntry.objects.filter(
            action='viewed_page', timestamp__date=d
        ).count()
        growth_days.append({'date': d.strftime('%a'), 'views': views})

    # ── Recent cases ──────────────────────────────────────────────────────────
    recent_agreements = Agreement.objects.order_by('-created_at')[:10]

    return render(request, 'admin_dashboard/dashboard.html', {
        # Operational metrics
        'active_cases':         active_cases,
        'waiting_count':        waiting_count,
        'disputed_count':       disputed_count,
        'avg_mttr':             avg_mttr,
        'auto_resolved_rate':   auto_resolved_rate,
        'auto_resolved_today':  auto_resolved_today,
        # Infrastructure
        'engine_status':        engine_status,
        'db_status':            db_status,
        'redis_status':         redis_status,
        'recent_errors':        recent_errors,
        'failed_logins':        failed_logins,
        # Visitor stats
        'total_page_views':     total_page_views,
        'unique_visitors':      unique_visitors,
        'total_views_today':    total_views_today,
        'growth_days':          growth_days,
        # Cases
        'recent_agreements':    recent_agreements,
    })
