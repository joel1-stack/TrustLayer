from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
from django.conf import settings
from ..models import PlatformSettings, AuditLogEntry
from apps.payments.adapters import registry as adapter_registry


def platform_settings(request):
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                actual_key = key.replace('setting_', '', 1)
                PlatformSettings.objects.update_or_create(key=actual_key, defaults={'value': value})
            elif key.startswith('payout_'):
                actual_key = key.replace('payout_', '', 1)
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

    payout_defaults = {
        'PLATFORM_BANK_NAME': 'ABSA Bank Kenya',
        'PLATFORM_BANK_ACCOUNT_NAME': 'Joel Kaunda',
        'PLATFORM_BANK_ACCOUNT_NUMBER': '',
        'PLATFORM_BANK_CODE': '',
        'PLATFORM_BRANCH_CODE': '',
        'PLATFORM_BANK_PHONE': '+254715641339',
        'PLATFORM_MPESA_NUMBER': '+254715641339',
    }
    for k, v in payout_defaults.items():
        if k not in all_settings:
            all_settings[k] = v

    try:
        providers = adapter_registry.list_providers()
    except Exception:
        providers = ['intasend', 'mpesa', 'stripe', 'bank_transfer']

    return render(request, 'admin_dashboard/settings.html', {
        'all_settings': all_settings,
        'payout_settings': ['PLATFORM_BANK_NAME', 'PLATFORM_BANK_ACCOUNT_NAME',
                            'PLATFORM_BANK_ACCOUNT_NUMBER', 'PLATFORM_BANK_CODE',
                            'PLATFORM_BRANCH_CODE', 'PLATFORM_BANK_PHONE',
                            'PLATFORM_MPESA_NUMBER'],
        'provider_status': {p: _check_provider(p) for p in providers},
    })


def _check_provider(provider_name):
    try:
        adapter = adapter_registry.get_adapter(provider_name)
        return {'name': provider_name, 'available': True, 'configured': _is_configured(provider_name)}
    except Exception:
        return {'name': provider_name, 'available': False, 'configured': False}


def _is_configured(provider_name):
    if provider_name == 'mpesa':
        return bool(getattr(settings, 'MPESA_CONSUMER_KEY', ''))
    elif provider_name == 'intasend':
        return bool(getattr(settings, 'INTASEND_SECRET_KEY', ''))
    elif provider_name == 'stripe':
        return bool(getattr(settings, 'STRIPE_API_KEY', ''))
    elif provider_name == 'bank_transfer':
        return True
    return False


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
