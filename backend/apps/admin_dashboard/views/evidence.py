import json, hashlib, io, csv
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum
from apps.agreements.models import Agreement, AgreementParty
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement
from apps.state_machine.models import StateTransition
from apps.conditions.models import Condition
from apps.notifications.models import NotificationEvent
from ..models import AuditLogEntry


def evidence_view(request):
    search = request.GET.get('search', '')
    agreements = Agreement.objects.all().order_by('-created_at')[:50]
    if search:
        agreements = Agreement.objects.filter(agreement_id__icontains=search).order_by('-created_at')[:50]

    return render(request, 'admin_dashboard/evidence.html', {
        'agreements': agreements,
        'search': search,
    })


def evidence_download(request, agreement_id):
    agreement = get_object_or_404(Agreement, agreement_id=agreement_id)
    parties = list(agreement.parties.all().values('role', 'name', 'identifier', 'split_percentage', 'split_fixed', 'payout_method'))
    conditions = list(Condition.objects.filter(agreement=agreement).values('condition_id', 'condition_type', 'status', 'description', 'created_at'))
    transitions = list(StateTransition.objects.filter(agreement=agreement).values('from_status', 'to_status', 'triggered_by', 'reason', 'created_at'))
    ledger = list(LedgerEntry.objects.filter(agreement=agreement).values('entry_type', 'amount', 'description', 'reference', 'created_at'))
    settlements = list(Settlement.objects.filter(agreement=agreement).values('settlement_id', 'amount', 'status', 'provider', 'provider_tx_id', 'created_at'))
    notifications = list(NotificationEvent.objects.filter(agreement=agreement).values('event_type', 'status', 'created_at'))

    data = {
        'agreement': {
            'agreement_id': agreement.agreement_id,
            'title': agreement.title,
            'amount': str(agreement.amount),
            'currency': agreement.currency,
            'status': agreement.status,
            'created_at': agreement.created_at.isoformat(),
            'updated_at': agreement.updated_at.isoformat(),
        },
        'parties': parties,
        'conditions': conditions,
        'transitions': transitions,
        'ledger': ledger,
        'settlements': settlements,
        'notifications': notifications,
        'exported_at': datetime.utcnow().isoformat(),
    }

    raw = json.dumps(data, indent=2, default=str)
    h = hashlib.sha256(raw.encode()).hexdigest()

    response = HttpResponse(raw, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="{agreement_id}_evidence.json"'
    response['X-Evidence-Hash'] = h
    return response


def evidence_export_all(request):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Agreement ID', 'Title', 'Amount', 'Currency', 'Status', 'Created', 'Updated'])

    for a in Agreement.objects.all().iterator():
        writer.writerow([a.agreement_id, a.title, str(a.amount), a.currency, a.status, a.created_at, a.updated_at])

    raw = output.getvalue()
    h = hashlib.sha256(raw.encode()).hexdigest()
    response = HttpResponse(raw, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="trustlayer_agreements_export.csv"'
    response['X-Evidence-Hash'] = h
    return response
