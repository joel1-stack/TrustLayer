from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from apps.agreements.models import Agreement, AgreementParty
from apps.conditions.models import Condition
from apps.state_machine.models import StateTransition
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement


def agreement_list(request):
    status_filter = request.GET.get('status', '')
    industry = request.GET.get('industry', '')
    search = request.GET.get('search', '')

    qs = Agreement.objects.all().select_related()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if industry:
        qs = qs.filter(metadata__industry=industry)
    if search:
        qs = qs.filter(Q(agreement_id__icontains=search) | Q(title__icontains=search))

    agreements = qs.order_by('-created_at')[:100]

    industries = Agreement.objects.values('metadata__industry').annotate(c=Count('id')).order_by('-c')[:10]

    statuses = ['CREATED', 'PAYMENT_PENDING', 'COLLECTED', 'WAITING', 'READY', 'SETTLING', 'SETTLED', 'DISPUTED', 'REFUNDED', 'CANCELLED']

    return render(request, 'admin_dashboard/agreements.html', {
        'agreements': agreements,
        'industries': industries,
        'statuses': statuses,
        'current_status': status_filter,
        'current_industry': industry,
        'current_search': search,
    })


def agreement_detail(request, agreement_id):
    agreement = get_object_or_404(Agreement, agreement_id=agreement_id)
    parties = agreement.parties.all()
    conditions = Condition.objects.filter(agreement=agreement).order_by('order')
    transitions = StateTransition.objects.filter(agreement=agreement).order_by('created_at')
    ledger = LedgerEntry.objects.filter(agreement=agreement).order_by('created_at')
    settlements = Settlement.objects.filter(agreement=agreement).order_by('-created_at')

    from django.db.models import Sum
    total_collected = ledger.filter(entry_type='CREDIT', description__icontains='Holding').aggregate(t=Sum('amount'))['t'] or 0

    return render(request, 'admin_dashboard/agreement_detail.html', {
        'agreement': agreement,
        'parties': parties,
        'conditions': conditions,
        'transitions': transitions,
        'ledger': ledger,
        'settlements': settlements,
        'total_collected': total_collected,
    })
