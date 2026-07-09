from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from apps.agreements.models import Agreement
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement


def portal_home(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_agreements = Agreement.objects.count()
    active = Agreement.objects.exclude(status__in=['SETTLED', 'REFUNDED', 'CANCELLED']).count()
    settled = Agreement.objects.filter(status='SETTLED').count()
    total_collected = LedgerEntry.objects.filter(entry_type='CREDIT').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_settled = Settlement.objects.filter(status='COMPLETED').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    recent = Agreement.objects.order_by('-created_at')[:10]

    return render(request, 'customer_portal/dashboard.html', {
        'total_agreements': total_agreements,
        'active_agreements': active,
        'settled_count': settled,
        'total_collected': total_collected,
        'total_settled': total_settled,
        'recent_agreements': recent,
    })


def portal_agreements(request):
    agreements = Agreement.objects.all().order_by('-created_at')[:50]
    return render(request, 'customer_portal/agreements.html', {'agreements': agreements})


def portal_ledger(request):
    entries = LedgerEntry.objects.all().order_by('-created_at')[:100]
    return render(request, 'customer_portal/ledger.html', {'entries': entries})


def portal_settlements(request):
    settlements = Settlement.objects.all().order_by('-created_at')[:50]
    return render(request, 'customer_portal/settlements.html', {'settlements': settlements})


def portal_developers(request):
    return render(request, 'customer_portal/developers.html')


def portal_settings(request):
    return render(request, 'customer_portal/settings.html')
