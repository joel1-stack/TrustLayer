import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from ..models import PlatformSettings, AuditLogEntry
from apps.payments.adapters.registry import get_adapter, list_providers, register_adapter

ENGINE_DEFINITIONS = {
    'agreement': {
        'name': 'Agreement Engine',
        'icon': '📋',
        'desc': 'Creates and manages agreements, parties, split rules. Routes money flows between buyers and sellers.',
        'fields': [
            {'key': 'engine_agreement_auto_approve', 'label': 'Auto-Approve Agreements', 'type': 'bool', 'default': 'true'},
            {'key': 'engine_agreement_max_amount', 'label': 'Max Agreement Amount (KES)', 'type': 'text', 'default': '1000000'},
            {'key': 'engine_agreement_require_verification', 'label': 'Require Email Verification', 'type': 'bool', 'default': 'true'},
        ],
        'test_action': 'Create and verify a test agreement',
        'endpoints': ['POST /api/agreements/', 'GET /api/agreements/<id>/'],
    },
    'ledger': {
        'name': 'Ledger Engine',
        'icon': '📊',
        'desc': 'Double-entry bookkeeping. Tracks every credit/debit per agreement and party.',
        'fields': [
            {'key': 'engine_ledger_auto_entry', 'label': 'Auto-Create Ledger Entries', 'type': 'bool', 'default': 'true'},
            {'key': 'engine_ledger_retention_days', 'label': 'Retention Period (days)', 'type': 'text', 'default': '365'},
        ],
        'test_action': 'Query ledger entries for an agreement',
        'endpoints': ['GET /api/ledger/<agreement_id>/', 'GET /internal/health/'],
    },
    'rule': {
        'name': 'Rule Engine',
        'icon': '⚖️',
        'desc': 'Split rules, fee rules, conditions. Defines how money is divided and when.',
        'fields': [
            {'key': 'TRUSTLAYER_PLATFORM_FEE_PERCENT', 'label': 'Platform Fee (%)', 'type': 'text', 'default': '5.00'},
            {'key': 'TRUSTLAYER_PLATFORM_PHONE', 'label': 'Platform Collection Phone', 'type': 'text', 'default': '+254715641339'},
            {'key': 'engine_rule_default_split', 'label': 'Default Split Mode', 'type': 'select', 'options': ['percentage', 'fixed', 'equally'], 'default': 'percentage'},
        ],
        'test_action': 'Calculate split for a sample agreement',
        'endpoints': ['POST /api/rules/calculate-split/', 'GET /api/rules/'],
    },
    'settlement': {
        'name': 'Settlement Engine',
        'icon': '💸',
        'desc': 'Pays out parties via M-Pesa, bank transfer, IntaSend, or Stripe. Tracks status.',
        'fields': [
            {'key': 'engine_settlement_retry_max', 'label': 'Max Retries on Failure', 'type': 'text', 'default': '3'},
            {'key': 'engine_settlement_auto_settle', 'label': 'Auto-Settle When Ready', 'type': 'bool', 'default': 'true'},
            {'key': 'engine_settlement_min_amount', 'label': 'Minimum Payout (KES)', 'type': 'text', 'default': '10'},
        ],
        'test_action': 'Trigger settlement for a READY agreement',
        'endpoints': ['POST /api/settlements/<agreement_id>/trigger/', 'GET /api/settlements/<agreement_id>/'],
    },
    'notification': {
        'name': 'Notification Engine',
        'icon': '🔔',
        'desc': 'Email, SMS, and webhook notifications for agreements, payments, and security alerts.',
        'fields': [
            {'key': 'security_alert_email', 'label': 'Alert Email', 'type': 'text', 'default': 'joelkaunda15@gmail.com'},
            {'key': 'security_alert_phone', 'label': 'Alert Phone', 'type': 'text', 'default': '+254715641339'},
            {'key': 'engine_notification_webhook_retries', 'label': 'Webhook Retries', 'type': 'text', 'default': '3'},
        ],
        'test_action': 'Send a test notification',
        'endpoints': ['POST /api/webhooks/test/', 'POST /api/notifications/test/'],
    },
    'audit': {
        'name': 'Audit Engine',
        'icon': '📝',
        'desc': 'Immutable SHA-256 chained audit log. Every admin action is recorded.',
        'fields': [
            {'key': 'engine_audit_retention_days', 'label': 'Retention Period (days)', 'type': 'text', 'default': '730'},
            {'key': 'engine_audit_hash_algorithm', 'label': 'Hash Algorithm', 'type': 'select', 'options': ['sha256', 'sha512'], 'default': 'sha256'},
        ],
        'test_action': 'Verify audit chain integrity',
        'endpoints': ['GET /api/audit/', 'GET /api/audit/verify/'],
    },
    'security': {
        'name': 'Security Engine',
        'icon': '🛡️',
        'desc': 'IP whitelist, rate limiting, brute force detection, session management.',
        'fields': [
            {'key': 'engine_security_max_login_attempts', 'label': 'Max Login Attempts', 'type': 'text', 'default': '5'},
            {'key': 'engine_security_lockout_minutes', 'label': 'Lockout Duration (min)', 'type': 'text', 'default': '30'},
            {'key': 'engine_security_session_timeout', 'label': 'Session Timeout (sec)', 'type': 'text', 'default': '1800'},
            {'key': 'engine_security_brute_force_threshold', 'label': 'Brute Force Alert Threshold/hr', 'type': 'text', 'default': '10'},
        ],
        'test_action': 'Run security health check',
        'endpoints': ['POST /api/security/check/', 'GET /api/security/log/'],
    },
    'orchestration': {
        'name': 'Orchestration Engine',
        'icon': '🎯',
        'desc': 'State machine conductor. Moves agreements through CREATED → SETTLED flow.',
        'fields': [
            {'key': 'engine_orchestration_immediate_split', 'label': 'Immediate Split (skip WAITING)', 'type': 'bool', 'default': 'true'},
            {'key': 'engine_orchestration_require_conditions', 'label': 'Require Conditions by Default', 'type': 'bool', 'default': 'false'},
        ],
        'test_action': 'Run full flow on test agreement',
        'endpoints': ['GET /internal/health/', 'POST /api/orchestration/trigger/<agreement_id>/'],
    },
}

PROVIDER_DEFINITIONS = {p: {'name': p.replace('_', ' ').title(), 'configured': False} for p in list_providers()}
for p in PROVIDER_DEFINITIONS:
    if p == 'mpesa':
        PROVIDER_DEFINITIONS[p]['configured'] = bool(getattr(settings, 'MPESA_CONSUMER_KEY', ''))
        PROVIDER_DEFINITIONS[p]['fields'] = ['MPESA_CONSUMER_KEY', 'MPESA_CONSUMER_SECRET', 'MPESA_SHORTCODE', 'MPESA_PASSKEY', 'MPESA_ENVIRONMENT']
    elif p == 'intasend':
        PROVIDER_DEFINITIONS[p]['configured'] = bool(getattr(settings, 'INTASEND_SECRET_KEY', ''))
        PROVIDER_DEFINITIONS[p]['fields'] = ['INTASEND_PUBLIC_KEY', 'INTASEND_SECRET_KEY', 'INTASEND_BASE_URL']
    elif p == 'stripe':
        PROVIDER_DEFINITIONS[p]['configured'] = bool(getattr(settings, 'STRIPE_API_KEY', ''))
        PROVIDER_DEFINITIONS[p]['fields'] = ['STRIPE_API_KEY', 'STRIPE_WEBHOOK_SECRET']
    elif p == 'bank_transfer':
        PROVIDER_DEFINITIONS[p]['configured'] = True
        PROVIDER_DEFINITIONS[p]['fields'] = ['PLATFORM_BANK_NAME', 'PLATFORM_BANK_ACCOUNT_NAME', 'PLATFORM_BANK_ACCOUNT_NUMBER', 'PLATFORM_BANK_CODE', 'PLATFORM_BRANCH_CODE']


def engines_overview(request):
    """Show all 8 engines + providers with status."""
    all_settings = {s.key: s.value for s in PlatformSettings.objects.all()}

    engines = []
    for eid, edef in ENGINE_DEFINITIONS.items():
        engine = dict(edef)
        engine['id'] = eid
        engine['enabled'] = all_settings.get(f'engine_{eid}_enabled', 'true') == 'true'
        engine['settings'] = {}
        for f in edef['fields']:
            engine['settings'][f['key']] = all_settings.get(f['key'], f.get('default', ''))
        engines.append(engine)

    providers = []
    for pid, pdef in PROVIDER_DEFINITIONS.items():
        p = dict(pdef)
        p['id'] = pid
        provider_settings = {}
        for f in pdef.get('fields', []):
            provider_settings[f] = all_settings.get(f, '')
        p['settings'] = provider_settings
        providers.append(p)

    return render(request, 'admin_dashboard/engines/overview.html', {
        'active_section': 'engines',
        'engines': engines,
        'providers': providers,
    })


def engine_detail(request, engine_id):
    """Configure a specific engine."""
    if engine_id not in ENGINE_DEFINITIONS:
        messages.error(request, f'Engine "{engine_id}" not found')
        return redirect('/admin/engines/')

    edef = ENGINE_DEFINITIONS[engine_id]
    all_settings = {s.key: s.value for s in PlatformSettings.objects.all()}

    if request.method == 'POST':
        for f in edef['fields']:
            val = request.POST.get(f['key'], '')
            PlatformSettings.objects.update_or_create(key=f['key'], defaults={'value': val})
        PlatformSettings.objects.update_or_create(
            key=f'engine_{engine_id}_enabled',
            defaults={'value': 'true' if request.POST.get('enabled') == 'on' else 'false'}
        )
        AuditLogEntry.objects.create(
            actor=request.session.get('admin_username', 'admin'),
            actor_ip=request.META.get('REMOTE_ADDR', ''),
            action='engine_updated',
            resource_type='engine',
            resource_id=engine_id,
        )
        messages.success(request, f'{edef["name"]} settings saved')
        return redirect(f'/admin/engines/{engine_id}/')

    settings_dict = {}
    for f in edef['fields']:
        settings_dict[f['key']] = all_settings.get(f['key'], f.get('default', ''))
    enabled = all_settings.get(f'engine_{engine_id}_enabled', 'true') == 'true'

    return render(request, 'admin_dashboard/engines/detail.html', {
        'active_section': 'engines',
        'engine': edef,
        'engine_id': engine_id,
        'settings': settings_dict,
        'enabled': enabled,
    })


@csrf_exempt
def engine_test(request, engine_id):
    """Test an engine's API endpoint."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if engine_id not in ENGINE_DEFINITIONS:
        return JsonResponse({'error': 'Engine not found'}, status=404)

    try:
        import urllib.request, json
        if engine_id == 'agreement':
            from apps.agreements.models import Agreement
            count = Agreement.objects.count()
            return JsonResponse({'status': 'ok', 'agreements': count})
        elif engine_id == 'ledger':
            from apps.ledger.models import LedgerEntry
            entries = LedgerEntry.objects.count()
            return JsonResponse({'status': 'ok', 'ledger_entries': entries})
        elif engine_id == 'rule':
            from apps.agreements.models import Agreement, AgreementParty
            a = Agreement.objects.filter(status='SETTLED').first()
            if a:
                from apps.agreements.services import AgreementService
                splits = AgreementService.calculate_splits(a)
                return JsonResponse({'status': 'ok', 'splits': [(s['party'].name, str(s['amount'])) for s in splits]})
            return JsonResponse({'status': 'ok', 'note': 'No SETTLED agreement to test splits'})
        elif engine_id == 'settlement':
            from apps.settlements.models import Settlement
            s = Settlement.objects.filter(status='COMPLETED').count()
            return JsonResponse({'status': 'ok', 'completed_settlements': s})
        elif engine_id == 'notification':
            return JsonResponse({'status': 'ok', 'note': 'Notification engine reachable'})
        elif engine_id == 'audit':
            from apps.admin_dashboard.models import AuditLogEntry
            entries = AuditLogEntry.objects.count()
            return JsonResponse({'status': 'ok', 'audit_entries': entries})
        elif engine_id == 'security':
            from apps.admin_dashboard.models import LoginAttempt
            fails = LoginAttempt.objects.filter(success=False).count()
            return JsonResponse({'status': 'ok', 'failed_logins': fails})
        elif engine_id == 'orchestration':
            from apps.agreements.models import Agreement
            counts = {}
            for s in ['CREATED', 'PAYMENT_PENDING', 'COLLECTED', 'WAITING', 'READY', 'SETTLING', 'SETTLED']:
                c = Agreement.objects.filter(status=s).count()
                if c:
                    counts[s] = c
            return JsonResponse({'status': 'ok', 'state_counts': counts})
        return JsonResponse({'status': 'ok', 'engine': engine_id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


def provider_config(request, provider_id):
    """Configure a payment provider."""
    if provider_id not in PROVIDER_DEFINITIONS:
        messages.error(request, f'Provider "{provider_id}" not found')
        return redirect('/admin/engines/')

    pdef = PROVIDER_DEFINITIONS[provider_id]
    all_settings = {s.key: s.value for s in PlatformSettings.objects.all()}

    if request.method == 'POST':
        for f in pdef.get('fields', []):
            val = request.POST.get(f, '')
            PlatformSettings.objects.update_or_create(key=f, defaults={'value': val})
        AuditLogEntry.objects.create(
            actor=request.session.get('admin_username', 'admin'),
            actor_ip=request.META.get('REMOTE_ADDR', ''),
            action='provider_updated',
            resource_type='provider',
            resource_id=provider_id,
        )
        messages.success(request, f'{pdef["name"]} settings saved')
        return redirect(f'/admin/engines/provider/{provider_id}/')

    settings_dict = {}
    for f in pdef.get('fields', []):
        settings_dict[f] = all_settings.get(f, '')

    return render(request, 'admin_dashboard/engines/provider.html', {
        'active_section': 'engines',
        'provider': pdef,
        'provider_id': provider_id,
        'settings': settings_dict,
    })


@csrf_exempt
def provider_test(request, provider_id):
    """Test a payment provider connection."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        adapter = get_adapter(provider_id)
        result = adapter.send_payout(amount=10, phone='+254715641339', reference='TEST_CONNECTION')
        return JsonResponse({'status': 'ok', 'provider': provider_id, 'result': result})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
