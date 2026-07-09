from django.shortcuts import render
from django.db.models import Sum, Q
from decimal import Decimal
from apps.ledger.models import LedgerEntry, LedgerAccount
from apps.agreements.models import Agreement


def ledger_view(request):
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')

    qs = LedgerEntry.objects.all().select_related('agreement', 'party')
    if search:
        qs = qs.filter(Q(agreement__agreement_id__icontains=search) | Q(reference__icontains=search) | Q(description__icontains=search))
    if type_filter:
        qs = qs.filter(entry_type=type_filter)

    entries = qs.order_by('-created_at')[:200]

    total_credits = LedgerEntry.objects.filter(entry_type='CREDIT').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_debits = LedgerEntry.objects.filter(entry_type='DEBIT').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    net = total_credits - total_debits
    total_entries = LedgerEntry.objects.count()

    accounts = LedgerAccount.objects.all().order_by('-balance')[:50]

    return render(request, 'admin_dashboard/ledger.html', {
        'entries': entries,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'net': net,
        'total_entries': total_entries,
        'accounts': accounts,
        'search': search,
        'type_filter': type_filter,
    })
