"""
TrustLayer V2 API — Organization-agnostic operational endpoints.

Flow: Case -> CONFIRMED -> SUBMITTED -> PENDING -> (Orchestrator pipeline)
Pipeline: Context -> Diagnosis -> Policy -> Action -> Verification

The API is organization-agnostic. Any bank, telco, e-commerce, or service
organization can use the same endpoints. Organization context is passed via
the `organization` slug.
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers_v2 import CreateCaseSerializer
from apps.agreements.models import Case, CaseParty
from apps.organizations.models import Organization
from apps.state_machine.services import StateMachine
from apps.core.constants import STATUS_CODES

logger = logging.getLogger(__name__)


def _run_pipeline(case):
    """Run the full System of Action pipeline on a case in PENDING state."""
    from apps.orchestration.services import Orchestrator

    context = Orchestrator.assemble_context(case)
    diagnosis = Orchestrator.diagnose(case, context)
    plans = Orchestrator.plan_action(case, diagnosis)
    if plans:
        results = Orchestrator.execute_actions(case, plans)
    else:
        results = []
    verification = Orchestrator.verify_outcome(case)

    case.refresh_from_db()
    return context, diagnosis, plans, verification


@api_view(['GET'])
@permission_classes([AllowAny])
def list_organizations(request):
    """
    List all active organizations.

    GET /api/v1/v2/organizations/
    """
    orgs = Organization.objects.filter(status='ACTIVE')
    return Response([
        {
            'slug': o.slug,
            'name': o.name,
            'type': o.org_type,
            'integration_mode': o.integration_mode,
            'supported_intents': o.supported_intents,
            'supported_channels': o.supported_channels,
            'brand_color': o.brand_color,
            'logo_url': o.logo_url,
        }
        for o in orgs
    ])


@api_view(['GET'])
@permission_classes([AllowAny])
def detect_organization(request):
    """
    Detect supported organizations by MCC/MNC (for telcos).

    GET /api/v1/v2/organizations/detect/?mcc=639&mnc=02
    """
    mcc = request.query_params.get('mcc', '')
    mnc = request.query_params.get('mnc', '')
    mcc_mnc = f"{mcc}{mnc}"

    orgs = Organization.objects.filter(
        status='ACTIVE',
        mcc_mnc__contains=[mcc_mnc]
    )

    return Response([
        {
            'slug': o.slug,
            'name': o.name,
            'type': o.org_type,
            'logo_url': o.logo_url,
            'brand_color': o.brand_color,
        }
        for o in orgs
    ])


@api_view(['POST'])
@permission_classes([AllowAny])
def create_operational_case(request):
    """
    Create a new case and run the System of Action pipeline.

    POST /api/v1/v2/cases/
    {
        "organization": "kcb",
        "title": "I don't recognize this transaction",
        "intent": "FRAUD_REPORT",
        "customer_ref": "KCB-12345",
        "channel": "WIDGET",
        "severity": "HIGH",
        "metadata": {}
    }
    """
    serializer = CreateCaseSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Resolve organization
    org = None
    org_slug = data.get('organization', '')
    if org_slug:
        try:
            org = Organization.objects.get(slug=org_slug, status='ACTIVE')
        except Organization.DoesNotExist:
            return Response(
                {'error': f'Organization "{org_slug}" not found or inactive'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Create case
    case = Case.objects.create(
        organization=org,
        title=data['title'],
        description=data.get('description', ''),
        intent=data['intent'],
        channel=data['channel'],
        severity=data['severity'],
        customer_ref=data.get('customer_ref', ''),
        amount=0,
        metadata={
            'msisdn': data.get('msisdn', ''),
            'location': data.get('location', ''),
            **data.get('metadata', {}),
        },
        creator_id=org_slug or 'unknown',
        creator_type='organization',
    )

    # Add customer party
    customer_identifier = data.get('customer_ref') or data.get('msisdn') or 'anonymous'
    CaseParty.objects.create(
        agreement=case,
        role='CUSTOMER',
        identifier=customer_identifier,
        name=customer_identifier,
    )

    # State machine: CREATED -> CONFIRMED -> SUBMITTED -> PENDING
    StateMachine.transition(
        case, 'CONFIRMED',
        triggered_by='api', actor_role='customer', channel=data['channel'],
        reason=f'Case validated for {org_slug}',
    )
    StateMachine.transition(
        case, 'SUBMITTED',
        triggered_by='api', actor_role='customer', channel=data['channel'],
        reason='Case submitted for processing',
    )
    StateMachine.transition(
        case, 'PENDING',
        triggered_by='api', actor_role='customer', channel=data['channel'],
        reason='Case pending context assembly',
    )

    # Run pipeline
    try:
        context, diagnosis, plans, verification = _run_pipeline(case)
        case.refresh_from_db()

        return Response({
            'case_id': case.case_id,
            'title': case.title,
            'status': case.status,
            'status_code': case.status_code_value,
            'organization': org_slug,
            'intent': data['intent'],
            'severity': data['severity'],
            'customer_ref': case.customer_ref,
            'diagnosis': {
                'root_cause': diagnosis.root_cause,
                'confidence': diagnosis.confidence,
                'recommended_actions': diagnosis.recommended_actions,
            },
            'context': {
                source: {k: v for k, v in ctx.items() if k != 'query_timestamp'}
                for source, ctx in context.items()
            },
            'verification': {
                'passed': verification.recovery_confirmed,
                'checks_total': verification.checks_total,
                'checks_passed': verification.checks_passed,
            },
            'created_at': case.created_at.isoformat(),
            'message': f'Case {case.case_id} created for {org_slug} and processed through System of Action.',
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f"Pipeline failed for case {case.case_id}")
        case.refresh_from_db()
        return Response({
            'case_id': case.case_id,
            'status': case.status,
            'status_code': case.status_code_value,
            'error': str(e),
            'message': f'Case created but pipeline failed: {str(e)}',
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def case_status(request, case_id):
    """Get case status with context, diagnosis, and verification data."""
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    from apps.context_engine.models import ContextRecord
    from apps.diagnosis_engine.models import DiagnosisRecord
    from apps.action_engine.models import ActionPlan
    from apps.verification_engine.models import VerificationResult

    context_records = ContextRecord.objects.filter(case=case)
    diagnosis = DiagnosisRecord.objects.filter(case=case).order_by('-created_at').first()
    action_plans = ActionPlan.objects.filter(case=case)
    verification = VerificationResult.objects.filter(case=case).order_by('-verified_at').first()

    context = {cr.source_adapter: cr.assembled_context for cr in context_records}

    org_slug = case.organization.slug if case.organization else ''

    return Response({
        'case_id': case.case_id,
        'title': case.title,
        'status': case.status,
        'status_code': case.status_code_value,
        'organization': org_slug,
        'intent': case.intent or case.metadata.get('intent', 'UNKNOWN'),
        'severity': case.severity or case.metadata.get('severity', 'NORMAL'),
        'customer_ref': case.customer_ref,
        'channel': case.channel,
        'context': context,
        'diagnosis': {
            'root_cause': diagnosis.root_cause if diagnosis else None,
            'confidence': diagnosis.confidence if diagnosis else None,
            'recommended_actions': diagnosis.recommended_actions if diagnosis else [],
        } if diagnosis else None,
        'actions': [
            {'action_type': p.action_type, 'status': p.status, 'parameters': p.parameters}
            for p in action_plans
        ],
        'verification': {
            'passed': verification.recovery_confirmed if verification else None,
            'checks_total': verification.checks_total if verification else 0,
            'checks_passed': verification.checks_passed if verification else 0,
        } if verification else None,
        'created_at': case.created_at.isoformat(),
        'updated_at': case.updated_at.isoformat(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def case_timeline(request, case_id):
    """Get case timeline -- all state transitions."""
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    from apps.state_machine.models import StateTransition
    transitions = StateTransition.objects.filter(agreement=case).order_by('created_at')

    timeline = [
        {
            'from_status': t.from_status,
            'to_status': t.to_status,
            'reason': t.reason,
            'triggered_by': t.triggered_by,
            'actor_role': t.actor_role,
            'channel': t.channel,
            'timestamp': t.created_at.isoformat(),
        }
        for t in transitions
    ]

    return Response({'case_id': case.case_id, 'timeline': timeline, 'count': len(timeline)})


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_resolution(request, case_id):
    """Customer feedback -- is the issue resolved?"""
    try:
        case = Case.objects.get(case_id=case_id)
    except Case.DoesNotExist:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    resolved = request.data.get('resolved', False)

    if resolved:
        from apps.verification_engine.models import VerificationResult
        VerificationResult.objects.create(
            case=case, overall_passed=True, checks_total=1,
            checks_passed=1, recovery_confirmed=True,
        )
        StateMachine.transition(
            case, 'SETTLED',
            triggered_by='customer', actor_role='customer', channel='api',
            reason='Customer confirmed resolution',
        )
        message = 'Case resolved. Thank you for confirming.'
    else:
        StateMachine.transition(
            case, 'DISPUTED',
            triggered_by='customer', actor_role='customer', channel='api',
            reason='Customer reports issue not resolved',
        )
        message = 'Case escalated. A specialist will review.'

    case.refresh_from_db()
    return Response({
        'case_id': case.case_id,
        'status': case.status,
        'status_code': case.status_code_value,
        'message': message,
    })
