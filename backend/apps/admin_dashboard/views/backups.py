import json, hashlib
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Count
from ..models import BackupRecord, AuditLogEntry
from apps.agreements.models import Agreement
from apps.settlements.models import Settlement
from apps.ledger.models import LedgerEntry


def backups_view(request):
    backups = BackupRecord.objects.all().order_by('-created_at')[:50]

    stats = {
        'total_agreements': Agreement.objects.count(),
        'total_ledger': LedgerEntry.objects.count(),
        'total_settlements': Settlement.objects.count(),
    }

    return render(request, 'admin_dashboard/backups.html', {
        'backups': backups,
        'stats': stats,
    })


def backup_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    label = request.POST.get('label', f'backup_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}')

    data = {
        'exported_at': datetime.utcnow().isoformat(),
        'agreements': list(Agreement.objects.all().values()),
        'settlements': list(Settlement.objects.all().values()),
        'ledger': list(LedgerEntry.objects.all().values()),
    }

    raw = json.dumps(data, indent=2, default=str)
    h = hashlib.sha256(raw.encode()).hexdigest()
    record_count = len(data['agreements']) + len(data['settlements']) + len(data['ledger'])

    bk = BackupRecord.objects.create(
        label=label,
        backup_type='manual',
        size_bytes=len(raw.encode()),
        sha256_hash=h,
        status='completed',
        record_count=record_count,
    )

    AuditLogEntry.objects.create(
        actor=request.session.get('admin_username', 'admin'),
        actor_ip=request.META.get('REMOTE_ADDR', ''),
        action='backup_created',
        resource_type='backup',
        resource_id=bk.backup_id,
        detail={'label': label, 'records': record_count},
    )

    return JsonResponse({'status': 'completed', 'backup_id': bk.backup_id, 'hash': h, 'records': record_count})


def backup_download(request, backup_id):
    bk = BackupRecord.objects.get(backup_id=backup_id)
    data = {
        'backup_id': bk.backup_id,
        'label': bk.label,
        'created_at': bk.created_at.isoformat(),
        'hash': bk.sha256_hash,
        'note': 'This is a backup record reference. Full data export available via Evidence Vault.',
    }
    raw = json.dumps(data, indent=2)
    response = HttpResponse(raw, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="backup_{bk.backup_id}.json"'
    return response
