from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from apps.agreements.models import Agreement, AgreementParty
from apps.conditions.models import Condition
from apps.state_machine.models import StateTransition
from apps.state_machine.services import StateMachine
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement
from apps.orchestration.services import Orchestrator


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

    from apps.agreements.models import STATUS_CODES
    statuses = list(STATUS_CODES.keys())

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

    can_release = agreement.status == 'HELD'
    can_settle = agreement.status == 'READY'
    has_pending_conditions = conditions.filter(status='PENDING', required=True).exists()

    return render(request, 'admin_dashboard/agreement_detail.html', {
        'agreement': agreement,
        'parties': parties,
        'conditions': conditions,
        'transitions': transitions,
        'ledger': ledger,
        'settlements': settlements,
        'total_collected': total_collected,
        'can_release': can_release,
        'can_settle': can_settle,
        'has_pending_conditions': has_pending_conditions,
    })


def agreement_action(request, agreement_id):
    if request.method != 'POST':
        return redirect('/admin/agreements/')
    agreement = get_object_or_404(Agreement, agreement_id=agreement_id)
    action = request.POST.get('action', '')
    ip = request.META.get('REMOTE_ADDR', '')

    try:
        if action == 'release':
            conditions = Condition.objects.filter(agreement=agreement, required=True, status='PENDING')
            for c in conditions:
                c.status = 'MET'
                c.met_at = timezone.now()
                c.save()
            Orchestrator.on_condition_met(agreement, conditions.first())
            messages.success(request, f'Agreement {agreement_id[:12]} released to READY')

        elif action == 'settle':
            Orchestrator.trigger_settlement(agreement)
            messages.success(request, f'Settlement triggered for {agreement_id[:12]}')

        elif action == 'cancel':
            StateMachine.transition(
                agreement, 'CANCELLED',
                triggered_by='admin_action',
                actor_role='super_admin',
                channel='admin_dashboard',
                ip_address=ip,
                reason=f'Manually cancelled by admin',
            )
            messages.success(request, f'Agreement {agreement_id[:12]} cancelled')

        elif action == 'refund':
            StateMachine.transition(
                agreement, 'REFUNDED',
                triggered_by='admin_action',
                actor_role='super_admin',
                channel='admin_dashboard',
                ip_address=ip,
                reason=f'Manually refunded by admin',
            )
            messages.success(request, f'Agreement {agreement_id[:12]} refunded')

        else:
            messages.error(request, f'Unknown action: {action}')
    except Exception as e:
        messages.error(request, f'Action failed: {e}')

    return redirect(f'/admin/agreements/{agreement_id}/')
