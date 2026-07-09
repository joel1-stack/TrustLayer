from django.shortcuts import render
from django.db.models import Q
from apps.agreements.models import Agreement
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement
from apps.notifications.models import NotificationEvent
from apps.state_machine.models import StateTransition
from apps.payments.models import WebhookEvent


def forensics_view(request):
    query = request.GET.get('q', '')
    result = None

    if query:
        agreements = Agreement.objects.filter(
            Q(agreement_id__icontains=query) |
            Q(parties__identifier__icontains=query)
        ).distinct()

        ledgers = LedgerEntry.objects.filter(
            Q(agreement__agreement_id__icontains=query) |
            Q(reference__icontains=query) |
            Q(party__identifier__icontains=query)
        )

        if agreements.exists():
            result = agreements.first()

        timeline = []
        if result:
            for t in StateTransition.objects.filter(agreement=result).order_by('created_at'):
                timeline.append({'time': t.created_at, 'event': f'State: {t.from_status} -> {t.to_status}', 'actor': t.triggered_by})
            for l in LedgerEntry.objects.filter(agreement=result).order_by('created_at'):
                timeline.append({'time': l.created_at, 'event': f'Ledger: {l.entry_type} {l.amount}', 'actor': 'ledger'})
            for n in NotificationEvent.objects.filter(agreement=result).order_by('created_at'):
                timeline.append({'time': n.created_at, 'event': f'Notification: {n.event_type}', 'actor': 'notification'})

    return render(request, 'admin_dashboard/forensics.html', {
        'query': query,
        'result': result,
        'timeline': timeline if query else [],
    })
