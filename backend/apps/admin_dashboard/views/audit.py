from django.shortcuts import render
from django.db.models import Q
from ..models import AuditLogEntry


def audit_view(request):
    search = request.GET.get('search', '')
    actor_filter = request.GET.get('actor', '')

    qs = AuditLogEntry.objects.all()
    if search:
        qs = qs.filter(Q(actor__icontains=search) | Q(action__icontains=search) | Q(resource_id__icontains=search) | Q(detail__icontains=search))
    if actor_filter:
        qs = qs.filter(actor=actor_filter)

    entries = qs.order_by('-timestamp')[:200]

    actors = AuditLogEntry.objects.values('actor').distinct().order_by('actor')

    return render(request, 'admin_dashboard/audit.html', {
        'entries': entries,
        'actors': actors,
        'search': search,
        'actor_filter': actor_filter,
    })
