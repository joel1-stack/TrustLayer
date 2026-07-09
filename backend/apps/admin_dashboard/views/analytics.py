import json
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from apps.agreements.models import Agreement
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement


def analytics_view(request):
    today = timezone.now().date()
    days = int(request.GET.get('days', 30))

    daily_revenue = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        total = LedgerEntry.objects.filter(
            entry_type='CREDIT', created_at__date=d,
            description__icontains='Platform'
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        daily_revenue.append({'date': d.isoformat(), 'amount': float(total)})

    industry_breakdown = Agreement.objects.values('metadata__industry').annotate(
        count=Count('id'), total=Sum('amount')
    ).order_by('-count')

    status_breakdown = Agreement.objects.values('status').annotate(
        count=Count('id'), total=Sum('amount')
    ).order_by('-count')

    avg_settlement_time = 0
    try:
        from apps.state_machine.models import StateTransition
        completed = StateTransition.objects.filter(to_status='SETTLED')
        for t in completed[:100]:
            avg_settlement_time += 1
    except Exception:
        pass

    return render(request, 'admin_dashboard/analytics.html', {
        'daily_revenue': json.dumps(daily_revenue),
        'industry_breakdown': industry_breakdown,
        'status_breakdown': status_breakdown,
        'days': days,
    })
