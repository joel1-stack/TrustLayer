import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from ..models import PlatformSettings, AuditLogEntry
from apps.payments.adapters.registry import get_adapter, list_providers, register_adapter

ENGINE_DEFINITIONS = {
    'context': {
        'name': 'Context Engine',
        'icon': '🔗',
        'desc': 'Assembles subscriber, billing, network, and device data from enterprise adapters into a unified case context.',
        'fields': [
            {'key': 'engine_context_timeout', 'label': 'Assembly Timeout (sec)', 'type': 'text', 'default': '30'},
            {'key': 'engine_context_parallel', 'label': 'Parallel Fetching', 'type': 'bool', 'default': 'true'},
            {'key': 'engine_context_cache_ttl', 'label': 'Cache TTL (sec)', 'type': 'text', 'default': '300'},
        ],
        'test_action': 'Assemble context for a test subscriber',
        'endpoints': ['POST /api/v1/v2/cases/', 'GET /api/v1/v2/cases/<id>/'],
    },
    'diagnosis': {
        'name': 'Diagnosis Engine',
        'icon': '🔍',
        'desc': 'Identifies root cause from assembled context using rule-based analysis and confidence scoring.',
        'fields': [
            {'key': 'engine_diagnosis_confidence_threshold', 'label': 'Min Confidence Threshold', 'type': 'text', 'default': '0.7'},
            {'key': 'engine_diagnosis_auto_escalate', 'label': 'Auto-Escalate Low Confidence', 'type': 'bool', 'default': 'true'},
        ],
        'test_action': 'Diagnose a test case',
        'endpoints': ['GET /api/v1/v2/cases/<id>/', 'GET /api/v1/v2/cases/<id>/timeline/'],
    },
    'policy': {
        'name': 'Policy Engine',
        'icon': '⚖️',
        'desc': 'Authorizes actions based on rules, risk level, and operator clearance. Enforces compliance.',
        'fields': [
            {'key': 'engine_policy_auto_approve', 'label': 'Auto-Approve Low Risk', 'type': 'bool', 'default': 'true'},
            {'key': 'engine_policy_max_risk_level', 'label': 'Max Auto-Approve Risk', 'type': 'select', 'options': ['LOW', 'MEDIUM', 'HIGH'], 'default': 'MEDIUM'},
        ],
        'test_action': 'Evaluate policy for a test action',
        'endpoints': ['POST /api/v1/v2/cases/', 'GET /api/v1/v2/cases/<id>/'],
    },
    'action': {
        'name': 'Action Engine',
        'icon': '⚡',
        'desc': 'Executes authorized remediation across enterprise systems — reactivation, config changes, credits.',
        'fields': [
            {'key': 'engine_action_retry_max', 'label': 'Max Retries on Failure', 'type': 'text', 'default': '3'},
            {'key': 'engine_action_timeout', 'label': 'Execution Timeout (sec)', 'type': 'text', 'default': '60'},
        ],
        'test_action': 'Execute a test remediation',
        'endpoints': ['POST /api/v1/v2/cases/', 'GET /api/v1/v2/cases/<id>/'],
    },
    'verification': {
        'name': 'Verification Engine',
        'icon': '✅',
        'desc': 'Confirms service recovery and validates expected outcomes after action execution.',
        'fields': [
            {'key': 'engine_verification_auto_verify', 'label': 'Auto-Verify Recovery', 'type': 'bool', 'default': 'true'},
            {'key': 'engine_verification_wait_seconds', 'label': 'Wait Before Verify (sec)', 'type': 'text', 'default': '10'},
        ],
        'test_action': 'Verify recovery for a test case',
        'endpoints': ['POST /api/v1/v2/cases/<id>/feedback/', 'GET /api/v1/v2/cases/<id>/'],
    },
    'truth': {
        'name': 'Truth Engine',
        'icon': '📜',
        'desc': 'Immutable audit trail with SHA-256 hash chains. Records every case transition and action.',
        'fields': [
            {'key': 'engine_truth_hash_algorithm', 'label': 'Hash Algorithm', 'type': 'select', 'options': ['sha256', 'sha512'], 'default': 'sha256'},
            {'key': 'engine_truth_retention_days', 'label': 'Retention Period (days)', 'type': 'text', 'default': '730'},
        ],
        'test_action': 'Verify audit chain integrity',
        'endpoints': ['GET /api/v1/v2/cases/<id>/timeline/', 'GET /api/v1/v2/cases/<id>/'],
    },
    'state_machine': {
        'name': 'State Machine',
        'icon': '🔄',
        'desc': 'Conducts case lifecycle — CREATED through SETTLED. Enforces valid transitions.',
        'fields': [
            {'key': 'engine_state_auto_advance', 'label': 'Auto-Advance States', 'type': 'bool', 'default': 'true'},
            {'key': 'engine_state_max_transitions', 'label': 'Max Transitions Per Case', 'type': 'text', 'default': '20'},
        ],
        'test_action': 'Run full lifecycle on test case',
        'endpoints': ['GET /api/v1/v2/cases/<id>/timeline/', 'POST /api/v1/v2/cases/'],
    },
}

PROVIDER_DEFINITIONS = {}


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
            from apps.agreements.models import Case as Agreement
            count = Agreement.objects.count()
            return JsonResponse({'status': 'ok', 'agreements': count})
        elif engine_id == 'ledger':
            from apps.ledger.models import LedgerEntry
            entries = LedgerEntry.objects.count()
            return JsonResponse({'status': 'ok', 'ledger_entries': entries})
        elif engine_id == 'rule':
            from apps.agreements.models import Case as Agreement, CaseParty as AgreementParty
            a = Agreement.objects.filter(status='SETTLED').first()
            if a:
                from apps.agreements.services import CaseService as AgreementService
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
            from apps.agreements.models import Case as Agreement
            from apps.core.constants import STATUS_CODES
            counts = {}
            for s in STATUS_CODES:
                c = Agreement.objects.filter(status=s).count()
                if c:
                    counts[f"{s} ({STATUS_CODES[s]})"] = c
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
