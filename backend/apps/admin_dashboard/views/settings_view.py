from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
from django.conf import settings
from ..models import PlatformSettings, AuditLogEntry


def platform_settings(request):
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                actual_key = key.replace('setting_', '', 1)
                PlatformSettings.objects.update_or_create(key=actual_key, defaults={'value': value})
        AuditLogEntry.objects.create(
            actor=request.session.get('admin_username', 'admin'),
            actor_ip=request.META.get('REMOTE_ADDR', ''),
            action='settings_updated',
            resource_type='settings',
        )
        messages.success(request, 'Settings saved')
        return redirect('/admin/settings/')

    all_settings = {}
    for s in PlatformSettings.objects.all():
        all_settings[s.key] = s.value

    defaults = {
        'TRUSTLAYER_PLATFORM_FEE_PERCENT': str(getattr(settings, 'TRUSTLAYER_PLATFORM_FEE_PERCENT', '5.00')),
        'TRUSTLAYER_PLATFORM_PHONE': getattr(settings, 'TRUSTLAYER_PLATFORM_PHONE', '+254715641339'),
    }
    for k, v in defaults.items():
        if k not in all_settings:
            all_settings[k] = v

    return render(request, 'admin_dashboard/settings.html', {
        'all_settings': all_settings,
    })


def reset_visitor_stats(request):
    if request.method == 'POST':
        count = AuditLogEntry.objects.filter(action='viewed_page').count()
        AuditLogEntry.objects.filter(action='viewed_page').delete()
        AuditLogEntry.objects.create(
            actor=request.session.get('admin_username', 'admin'),
            actor_ip=request.META.get('REMOTE_ADDR', ''),
            action='reset_visitor_stats',
            resource_type='stats',
            detail={'deleted_entries': count},
        )
        messages.success(request, f'Visitor stats reset. {count} entries cleared.')
        return redirect('/admin/dashboard/')
    return JsonResponse({'error': 'POST required'}, status=405)
