"""
TrustLayer V2 API — Operational endpoints for the System of Action.

Flow: Case → CONFIRMED → SUBMITTED → PENDING → (Orchestrator pipeline)
Pipeline: Context → Diagnosis → Policy → Action → Verification
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers_v2 import CreateCaseSerializer
from apps.agreements.models import Case, CaseParty
from apps.state_machine.services import StateMachine
from apps.core.constants import STATUS_CODES

logger = logging.getLogger(__name__)


def _run_pipeline(case):
    """Run the full System of Action pipeline on a case in PENDING state."""
    from apps.orchestration.services import Orchestrator

    # Phase 1: Context Assembly (transitions PENDING → AVAILABLE)
    context = Orchestrator.assemble_context(case)

    # Phase 2: Diagnosis (transitions AVAILABLE → RECONCILING)
    diagnosis = Orchestrator.diagnose(case, context)

    # Phase 3: Policy + Action Planning (transitions RECONCILING → DISPUTED)
    plans = Orchestrator.plan_action(case, diagnosis)

    # Phase 4: Action Execution (transitions DISPUTED → HELD)
    if plans:
        results = Orchestrator.execute_actions(case, plans)
    else:
        results = []

    # Phase 5: Verification (transitions HELD → RECONCILING or stays)
    verification = Orchestrator.verify_outcome(case)

    case.refresh_from_db()
    return context, diagnosis, plans, verification


@api_view(['POST'])
@permission_classes([AllowAny])
def create_operational_case(request):
    """
    Create a new operational case and run the System of Action pipeline.

    POST /api/v1/v2/cases/
    {
        "title": "Mobile data not working",
        "intent": "DATA_FAILURE",
        "msisdn": "+254712345678",
        "severity": "NORMAL",
        "channel": "WEB"
    }
    """
    serializer = CreateCaseSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Create case with amount=0 (operational, not financial)
    case = Case.objects.create(
        title=data['title'],
        description=data.get('description', ''),
        amount=0,
        metadata={
            'intent': data['intent'],
            'severity': data['severity'],
            'channel': data['channel'],
            'msisdn': data['msisdn'],
            'location': data.get('location', ''),
            'provider': data.get('provider', ''),
            **data.get('metadata', {}),
        },
        creator_id=data['msisdn'],
        creator_type='customer',
    )

    # Add customer party
    CaseParty.objects.create(
        agreement=case,
        role='CUSTOMER',
        identifier=data['msisdn'],
        name=data['msisdn'],
    )

    # Follow the state machine: CREATED → CONFIRMED → SUBMITTED → PENDING
    StateMachine.transition(
        case, 'CONFIRMED',
        triggered_by='api', actor_role='customer', channel=data['channel'],
        reason='Operational case validated',
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

    # Run the pipeline
    try:
        context, diagnosis, plans, verification = _run_pipeline(case)
        case.refresh_from_db()

        return Response({
            'case_id': case.case_id,
            'title': case.title,
            'status': case.status,
            'status_code': case.status_code_value,
            'intent': data['intent'],
            'severity': data['severity'],
            'msisdn': data['msisdn'],
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
            'message': f'Case {case.case_id} created and processed through System of Action.',
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

    return Response({
        'case_id': case.case_id,
        'title': case.title,
        'status': case.status,
        'status_code': case.status_code_value,
        'intent': case.metadata.get('intent', 'UNKNOWN'),
        'severity': case.metadata.get('severity', 'NORMAL'),
        'msisdn': case.metadata.get('msisdn', ''),
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
    """Get case timeline — all state transitions."""
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
    """Customer feedback — is the issue resolved?"""
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
