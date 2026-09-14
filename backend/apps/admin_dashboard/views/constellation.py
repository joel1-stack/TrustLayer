import json
from django.http import JsonResponse
from django.shortcuts import render
from ..models import PlatformSettings
from apps.context_engine.models import ContextRecord
from apps.diagnosis_engine.models import DiagnosisRecord
from apps.policy_engine.models import PolicyRule, PolicyDecision
from apps.action_engine.models import ActionPlan, ActionResult
from apps.verification_engine.models import VerificationCheck, VerificationResult
from apps.agreements.models import Case


def constellation_view(request):
    """3D Engine Constellation visualization."""
    stats = {
        'cases_total': Case.objects.count(),
        'cases_active': Case.objects.exclude(status__in=['SETTLED', 'CANCELLED', 'FAILED']).count(),
        'context_records': ContextRecord.objects.count(),
        'diagnoses': DiagnosisRecord.objects.count(),
        'policy_rules': PolicyRule.objects.count(),
        'policy_decisions': PolicyDecision.objects.count(),
        'action_plans': ActionPlan.objects.count(),
        'action_results': ActionResult.objects.count(),
        'verification_checks': VerificationCheck.objects.count(),
        'verification_results': VerificationResult.objects.count(),
    }
    return render(request, 'admin_dashboard/constellation.html', {
        'active_section': 'constellation',
        'stats': stats,
    })


def constellation_api(request):
    """API endpoint for constellation data."""
    engines = [
        {
            'id': 'context',
            'name': 'Context Engine',
            'icon': '🔗',
            'desc': 'Assembles operational context from enterprise adapters',
            'color': '#3b82f6',
            'stats': {
                'records': ContextRecord.objects.count(),
                'success': ContextRecord.objects.filter(status='success').count(),
                'failed': ContextRecord.objects.filter(status='failed').count(),
            },
        },
        {
            'id': 'diagnosis',
            'name': 'Diagnosis Engine',
            'icon': '🔍',
            'desc': 'Identifies root cause from assembled context',
            'color': '#8b5cf6',
            'stats': {
                'records': DiagnosisRecord.objects.count(),
                'avg_confidence': 0.85,
            },
        },
        {
            'id': 'policy',
            'name': 'Policy Engine',
            'icon': '⚖️',
            'desc': 'Authorizes actions based on rules and risk',
            'color': '#f59e0b',
            'stats': {
                'rules': PolicyRule.objects.count(),
                'decisions': PolicyDecision.objects.count(),
                'approved': PolicyDecision.objects.filter(decision='approved').count(),
            },
        },
        {
            'id': 'action',
            'name': 'Action Engine',
            'icon': '⚡',
            'desc': 'Executes authorized remediation actions',
            'color': '#10b981',
            'stats': {
                'plans': ActionPlan.objects.count(),
                'completed': ActionResult.objects.filter(outcome='success').count(),
                'failed': ActionResult.objects.filter(outcome='failed').count(),
            },
        },
        {
            'id': 'verification',
            'name': 'Verification Engine',
            'icon': '✅',
            'desc': 'Confirms service recovery after action',
            'color': '#06b6d4',
            'stats': {
                'checks': VerificationCheck.objects.count(),
                'passed': VerificationCheck.objects.filter(passed=True).count(),
                'recovery': VerificationResult.objects.filter(recovery_confirmed=True).count(),
            },
        },
        {
            'id': 'adapters',
            'name': 'Enterprise Adapters',
            'icon': '🏢',
            'desc': 'Mock HLR, Billing, Network, Device systems',
            'color': '#64748b',
            'stats': {
                'adapters': 4,
                'active': 4,
            },
        },
        {
            'id': 'truth',
            'name': 'Truth Engine',
            'icon': '📋',
            'desc': 'Immutable audit trail and evidence chain',
            'color': '#ec4899',
            'stats': {
                'cases': Case.objects.count(),
            },
        },
    ]

    connections = [
        {'from': 'adapters', 'to': 'context', 'label': 'raw data'},
        {'from': 'context', 'to': 'diagnosis', 'label': 'assembled context'},
        {'from': 'diagnosis', 'to': 'policy', 'label': 'root cause'},
        {'from': 'policy', 'to': 'action', 'label': 'authorized plan'},
        {'from': 'action', 'to': 'verification', 'label': 'executed action'},
        {'from': 'verification', 'to': 'truth', 'label': 'verified outcome'},
        {'from': 'truth', 'to': 'context', 'label': 'feedback loop'},
    ]

    return JsonResponse({'engines': engines, 'connections': connections})
