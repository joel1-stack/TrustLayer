import json
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.conf import settings
from apps.agreements.models import Agreement
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement
from apps.payments.models import WebhookEvent
from ..models import AdminUser, LoginAttempt, AuditLogEntry


def dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    agreements_today = Agreement.objects.filter(created_at__date=today).count()
    agreements_month = Agreement.objects.filter(created_at__date__gte=month_start).count()
    total_agreements = Agreement.objects.count()

    from apps.agreements.models import STATUS_CATEGORIES, STATUS_CODES
    terminal_states = [s for s, c in STATUS_CATEGORIES.items() if c == 'terminal']
    active_agreements = Agreement.objects.exclude(status__in=terminal_states).count()
    held_count = Agreement.objects.filter(status='HELD').count()
    waiting_count = Agreement.objects.filter(status__in=['PENDING_KYC', 'PENDING', 'SUBMITTED']).count()
    disputed_count = Agreement.objects.filter(status='DISPUTED').count()
    failed_count = Agreement.objects.filter(status__in=['FAILED', 'FAILED_PERMANENT']).count()
    settled_today = Agreement.objects.filter(status='SETTLED', updated_at__date=today).count()

    collected_today = LedgerEntry.objects.filter(
        entry_type='CREDIT', created_at__date=today,
        description__icontains='Holding'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    collected_month = LedgerEntry.objects.filter(
        entry_type='CREDIT', created_at__date__gte=month_start,
        description__icontains='Holding'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    platform_fees_today = LedgerEntry.objects.filter(
        entry_type='CREDIT', created_at__date=today,
        description__icontains='Platform'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    platform_fees_month = LedgerEntry.objects.filter(
        entry_type='CREDIT', created_at__date__gte=month_start,
        description__icontains='Platform'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    total_settled = LedgerEntry.objects.filter(
        entry_type='DEBIT', description__icontains='Settled'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    pending_settlement_amount = LedgerEntry.objects.filter(
        entry_type='CREDIT', created_at__date__gte=month_start
    ).exclude(description__icontains='Settled').exclude(description__icontains='Platform').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    failed_logins = LoginAttempt.objects.filter(success=False, timestamp__date=today).count()
    blocked_ips = LoginAttempt.objects.filter(success=False, timestamp__date=today).values('ip_address').distinct().count()

    recent_logins = LoginAttempt.objects.filter(timestamp__date=today).order_by('-timestamp')[:20]

    recent_agreements = Agreement.objects.order_by('-created_at')[:10]

    industries = Agreement.objects.values('metadata__industry').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    engine_status = {
        'agreement': 'running', 'state_machine': 'running', 'condition': 'running',
        'ledger': 'running', 'settlement': 'running', 'notification': 'running',
        'webhook_receiver': 'running', 'orchestration': 'running',
    }

    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            db_status = 'connected'
    except Exception:
        db_status = 'error'

    try:
        import redis
        r = redis.from_url(getattr(settings, 'REDIS_URL', 'redis://localhost:6379'))
        r.ping()
        redis_status = 'connected'
    except Exception:
        redis_status = 'error'

    recent_errors = WebhookEvent.objects.filter(error__isnull=False).order_by('-created_at')[:5]

    # Visitor growth tracking
    total_page_views = AuditLogEntry.objects.filter(action='viewed_page').count()
    unique_visitors = AuditLogEntry.objects.filter(action='viewed_page').values('actor_ip').distinct().count()
    growth_days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        views = AuditLogEntry.objects.filter(action='viewed_page', timestamp__date=d).count()
        growth_days.append({'date': d.strftime('%a'), 'views': views})
    total_views_today = AuditLogEntry.objects.filter(action='viewed_page', timestamp__date=today).count()

    return render(request, 'admin_dashboard/dashboard.html', {
        'agreements_today': agreements_today,
        'agreements_month': agreements_month,
        'total_agreements': total_agreements,
        'active_agreements': active_agreements,
        'waiting_count': waiting_count,
        'held_count': held_count,
        'disputed_count': disputed_count,
        'failed_count': failed_count,
        'settled_today': settled_today,
        'collected_today': collected_today,
        'collected_month': collected_month,
        'platform_fees_today': platform_fees_today,
        'platform_fees_month': platform_fees_month,
        'total_settled': total_settled,
        'pending_settlement_amount': pending_settlement_amount,
        'failed_logins': failed_logins,
        'blocked_ips': blocked_ips,
        'recent_logins': recent_logins,
        'recent_agreements': recent_agreements,
        'industries': industries,
        'engine_status': engine_status,
        'db_status': db_status,
        'redis_status': redis_status,
        'recent_errors': recent_errors,
        'total_page_views': total_page_views,
        'unique_visitors': unique_visitors,
        'total_views_today': total_views_today,
        'growth_days': growth_days,
    })
