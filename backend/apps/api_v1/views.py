from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse
from apps.agreements.models import Case, CaseTimeline, CaseMessage, CaseEvidence
from apps.state_machine.services import StateMachine


def _case_payload(case):
    timeline = CaseTimeline.objects.filter(case=case).order_by('created_at')
    messages = case.messages.all().order_by('created_at')
    evidence = case.evidence_items.all().order_by('-created_at')
    return {
        'case_id': case.case_id,
        'status': case.status,
        'status_code': case.status_code,
        'problem_type': case.problem_type,
        'problem_label': case.problem_label,
        'txn_id': case.txn_id,
        'amount': str(case.amount),
        'currency': case.currency,
        'description': case.description,
        'date_occurred': case.date_occurred.isoformat() if case.date_occurred else None,
        'customer_name': case.customer_name,
        'customer_email': case.customer_email,
        'customer_phone': case.customer_phone,
        'contact': case.contact,
        'priority': case.priority,
        'assigned_team': case.assigned_team,
        'investigation_notes': case.investigation_notes,
        'finding': case.finding,
        'resolution_type': case.resolution_type,
        'resolution_label': case.resolution_label,
        'resolution_note': case.resolution_note,
        'resolved_by': case.resolved_by,
        'customer_verified': case.customer_verified,
        'verification_note': case.verification_note,
        'created_at': case.created_at.isoformat() if case.created_at else None,
        'updated_at': case.updated_at.isoformat() if case.updated_at else None,
        'timeline': [{
            'from_status': t.from_status,
            'to_status': t.to_status,
            'reason': t.reason,
            'triggered_by': t.triggered_by,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        } for t in timeline],
        'messages': [{
            'sender': m.sender,
            'sender_type': m.sender_type,
            'text': m.text,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        } for m in messages],
        'evidence': [{
            'evidence_type': e.evidence_type,
            'url': e.url,
            'filename': e.filename,
            'description': e.description,
            'uploaded_by': e.uploaded_by,
            'created_at': e.created_at.isoformat() if e.created_at else None,
        } for e in evidence],
    }


# ──────────────────────────────────────────────────────────────────────────────
# LIST CASES
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='List all cases',
    description=(
        'Returns up to 50 cases, ordered by newest first.\n\n'
        '**Lifecycle position:** This returns cases at any stage of the loop:\n'
        '`OPEN → EVIDENCE_COLLECTION → INVESTIGATING → RESOLUTION_RECORDED → VERIFYING → RESOLVED → CLOSED`\n\n'
        'Use the `status` field in each case to filter by lifecycle stage.'
    ),
    responses={200: OpenApiResponse(description='Array of case objects')},
    tags=['Cases'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def list_cases_api(request):
    cases = Case.objects.all()[:50]
    data = [{
        'case_id': c.case_id,
        'status': c.status,
        'problem_type': c.problem_type,
        'problem_label': c.problem_label,
        'description': c.description,
        'txn_id': c.txn_id,
        'amount': str(c.amount),
        'currency': c.currency,
        'customer_name': c.customer_name,
        'priority': c.priority,
        'assigned_team': c.assigned_team,
        'resolution_type': c.resolution_type,
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
    } for c in cases]
    return Response(data)


# ──────────────────────────────────────────────────────────────────────────────
# CREATE CASE  (Step 1 of the lifecycle)
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Create a new case',
    description=(
        '**Step 1 — Report**\n\n'
        'Creates a new case and places it in `OPEN` status. This is the entry point '
        'of the entire lifecycle loop.\n\n'
        '```\n'
        '         ┌──────────┐\n'
        '         │  CREATE  │ ← You are here\n'
        '         │  (OPEN)  │\n'
        '         └────┬─────┘\n'
        '              │\n'
        '              ▼\n'
        '    ┌─────────────────┐\n'
        '    │ EVIDENCE_COLLECTION │\n'
        '    └────────┬────────┘\n'
        '             │\n'
        '             ▼\n'
        '    ┌─────────────────┐\n'
        '    │  INVESTIGATING  │\n'
        '    └────────┬────────┘\n'
        '             │\n'
        '             ▼\n'
        '    ┌─────────────────┐\n'
        '    │ RESOLUTION_     │\n'
        '    │ RECORDED        │\n'
        '    └────────┬────────┘\n'
        '             │\n'
        '             ▼\n'
        '    ┌─────────────────┐\n'
        '    │   VERIFYING     │\n'
        '    └────────┬────────┘\n'
        '             │\n'
        '      ┌──────┴──────┐\n'
        '      ▼             ▼\n'
        ' ┌──────────┐  ┌──────────┐\n'
        ' │ RESOLVED │  │ REOPENED │\n'
        ' └────┬─────┘  └────┬─────┘\n'
        '      │             │\n'
        '      ▼             └──→ INVESTIGATING\n'
        ' ┌──────────┐\n'
        ' │  CLOSED  │\n'
        ' └──────────┘\n'
        '```\n\n'
        '**Routing:** The case is automatically assigned to a team based on `problem_type`:\n'
        '- `TRANSACTION_DISPUTE` → FRAUD_OPERATIONS\n'
        '- `PAYMENT_PROBLEM` → PAYMENTS_OPERATIONS\n'
        '- `ACCOUNT_PROBLEM` → ACCOUNT_SECURITY\n'
        '- `OTHER` → GENERAL_SUPPORT\n\n'
        '**Priority:** Set automatically — `HIGH` if amount > 10,000, else `NORMAL`.'
    ),
    request={
        'application/json': {
            'type': 'object',
            'required': ['description'],
            'properties': {
                'problem_type': {'type': 'string', 'enum': ['TRANSACTION_DISPUTE', 'PAYMENT_PROBLEM', 'ACCOUNT_PROBLEM', 'OTHER'], 'default': 'TRANSACTION_DISPUTE'},
                'txn_id': {'type': 'string', 'description': 'Transaction reference ID', 'example': 'TXN-8839201'},
                'amount': {'type': 'number', 'description': 'Disputed amount', 'example': 50000},
                'currency': {'type': 'string', 'default': 'KES'},
                'description': {'type': 'string', 'description': 'What happened — customer statement', 'example': 'I did not make this payment. Someone accessed my account.'},
                'date_occurred': {'type': 'string', 'format': 'date', 'example': '2026-09-15'},
                'customer_name': {'type': 'string', 'example': 'Jane Doe'},
                'customer_email': {'type': 'string', 'example': 'jane@example.com'},
                'customer_phone': {'type': 'string', 'example': '+254712345678'},
                'priority': {'type': 'string', 'enum': ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'], 'description': 'Auto-set if omitted'},
            },
        }
    },
    examples=[
        OpenApiExample(
            'Transaction dispute',
            summary='Customer reports unauthorized mobile money transfer',
            value={
                'problem_type': 'TRANSACTION_DISPUTE',
                'txn_id': 'TXN-8839201',
                'amount': 50000,
                'currency': 'KES',
                'description': 'I did not make this payment. Someone accessed my account and transferred KES 50,000.',
                'date_occurred': '2026-09-15',
                'customer_name': 'Jane Doe',
                'customer_email': 'jane@example.com',
                'customer_phone': '+254712345678',
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            description='Case created successfully',
            examples=[OpenApiExample('Created', value={'case_id': 'CASE4DRUHSCT4F', 'status': 'OPEN', 'message': 'Case CASE4DRUHSCT4F created.'})],
        ),
        400: OpenApiResponse(description='Missing required fields'),
    },
    tags=['Cases'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def create_case_api(request):
    data = request.data
    description = data.get('description', '')
    if not description:
        return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = float(data.get('amount', 0) or 0)
    except (ValueError, TypeError):
        amount = 0

    problem_type = data.get('problem_type', 'TRANSACTION_DISPUTE')
    from apps.core.constants import TEAM_BY_PROBLEM
    assigned_team = TEAM_BY_PROBLEM.get(problem_type, 'FRAUD_OPERATIONS')

    case = Case.objects.create(
        problem_type=problem_type,
        txn_id=data.get('txn_id', ''),
        amount=amount,
        currency=data.get('currency', 'KES'),
        description=description,
        date_occurred=data.get('date_occurred') or None,
        customer_name=data.get('customer_name', ''),
        customer_email=data.get('customer_email', ''),
        customer_phone=data.get('customer_phone', ''),
        priority=data.get('priority', 'HIGH' if amount > 10000 else 'NORMAL'),
        assigned_team=assigned_team,
        status='OPEN',
    )
    CaseTimeline.objects.create(case=case, from_status='', to_status='OPEN', reason='Case created by customer', triggered_by='customer')

    return Response({
        'case_id': case.case_id,
        'status': case.status,
        'message': f'Case {case.case_id} created.'
    }, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# CASE DETAIL
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Get case details',
    description=(
        'Returns the full case record including timeline, messages, and evidence.\n\n'
        'The `timeline` array shows every state transition in chronological order.\n'
        'The `messages` array shows all customer/agent messages.\n'
        'The `evidence` array shows all uploaded files.'
    ),
    responses={200: OpenApiResponse(description='Full case object with timeline, messages, evidence')},
    tags=['Cases'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def case_detail_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    return Response(_case_payload(case))


# ──────────────────────────────────────────────────────────────────────────────
# ADD EVIDENCE  (Step 2 of the lifecycle)
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Add evidence to a case',
    description=(
        '**Step 2 — Evidence Collection**\n\n'
        'Attaches a file or reference to the case. If the case is in `OPEN` status, '
        'it automatically transitions to `EVIDENCE_COLLECTION`.\n\n'
        'Evidence can be screenshots, PDFs, bank statements, or any file that supports the case.'
    ),
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'evidence_type': {'type': 'string', 'enum': ['screenshot', 'document', 'audio', 'video'], 'default': 'screenshot'},
                'url': {'type': 'string', 'description': 'URL if evidence is hosted online'},
                'filename': {'type': 'string', 'example': 'bank_sms.png'},
                'description': {'type': 'string', 'example': 'SMS confirmation of the transfer'},
                'uploaded_by': {'type': 'string', 'default': 'customer'},
            },
        }
    },
    responses={
        201: OpenApiResponse(description='Evidence added', examples=[OpenApiExample('Added', value={'status': 'evidence added'})]),
    },
    tags=['Evidence'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def collect_evidence_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    if case.status == 'OPEN':
        StateMachine.transition(case, 'EVIDENCE_COLLECTION', triggered_by='customer', reason='Customer provided evidence')

    data = request.data
    CaseEvidence.objects.create(
        case=case,
        evidence_type=data.get('evidence_type', 'screenshot'),
        url=data.get('url', ''),
        filename=data.get('filename', ''),
        description=data.get('description', ''),
        uploaded_by=data.get('uploaded_by', 'customer'),
    )

    return Response({'status': 'evidence added'}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# START INVESTIGATION  (Step 3 of the lifecycle)
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Start investigation',
    description=(
        '**Step 3 — Investigate**\n\n'
        'Agent picks up the case and begins investigation. Transitions the case to `INVESTIGATING`.\n\n'
        'Valid from: `OPEN`, `EVIDENCE_COLLECTION`, `REOPENED`, `ESCALATED`'
    ),
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'agent_id': {'type': 'string', 'description': 'Agent identifier', 'example': 'joelkaunda15'},
            },
        }
    },
    responses={200: OpenApiResponse(description='Case status after transition')},
    tags=['Investigation'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def start_investigation_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    agent_id = request.data.get('agent_id', 'agent')

    if case.status in ['OPEN', 'EVIDENCE_COLLECTION', 'REOPENED', 'ESCALATED']:
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_id, reason='Agent started investigation')

    return Response({'status': case.status})


# ──────────────────────────────────────────────────────────────────────────────
# RESOLVE CASE  (Step 4 of the lifecycle)
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Record resolution',
    description=(
        '**Step 4 — Resolve**\n\n'
        'Agent records the outcome of the investigation. Transitions to `RESOLUTION_RECORDED`.\n\n'
        'This does NOT close the case. The customer must verify the resolution first.\n\n'
        'Valid from: `INVESTIGATING`, `ESCALATED`, `OPEN`, `EVIDENCE_COLLECTION`, `REOPENED`'
    ),
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'resolution_type': {'type': 'string', 'enum': ['CONFIRMED_FRAUD', 'TRANSACTION_LEGITIMATE', 'CUSTOMER_ERROR', 'UNABLE_TO_DETERMINE', 'REFUNDED']},
                'finding': {'type': 'string', 'description': 'Brief finding summary', 'example': 'Unauthorized device access from new IP'},
                'note': {'type': 'string', 'description': 'Detailed resolution note shown to customer', 'example': 'Transaction was from unrecognized device in Lagos. Refund initiated.'},
                'agent_id': {'type': 'string', 'example': 'joelkaunda15'},
            },
        }
    },
    responses={200: OpenApiResponse(description='Case moved to RESOLUTION_RECORDED')},
    tags=['Resolution'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def resolve_case_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    data = request.data

    if case.status not in ['INVESTIGATING', 'ESCALATED', 'OPEN', 'EVIDENCE_COLLECTION', 'REOPENED']:
        return Response({'error': f'Cannot resolve from {case.status}'}, status=status.HTTP_400_BAD_REQUEST)

    if case.status in ['OPEN', 'EVIDENCE_COLLECTION', 'REOPENED']:
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=data.get('agent_id', 'agent'), reason='Agent picked up case')
    if case.status == 'ESCALATED':
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=data.get('agent_id', 'agent'), reason='Escalation addressed')

    StateMachine.transition(case, 'RESOLUTION_RECORDED', triggered_by=data.get('agent_id', 'agent'), reason='Resolution recorded')

    case.resolution_type = data.get('resolution_type', '')
    case.resolution_note = data.get('note', '')
    case.finding = data.get('finding', '')
    case.resolved_by = data.get('agent_id', 'agent')
    case.save()

    return Response({'case_id': case.case_id, 'status': case.status})


# ──────────────────────────────────────────────────────────────────────────────
# SEND FOR VERIFICATION  (Step 5a — system sends to customer)
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Send to customer for verification',
    description=(
        '**Step 5 — Verify (system side)**\n\n'
        'Moves the case from `RESOLUTION_RECORDED` to `VERIFYING`.\n'
        'This notifies the customer that a resolution has been recorded and asks them to confirm.\n\n'
        'Valid from: `RESOLUTION_RECORDED` only.'
    ),
    responses={200: OpenApiResponse(description='Case moved to VERIFYING')},
    tags=['Verification'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_case_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)

    if case.status != 'RESOLUTION_RECORDED':
        return Response({'error': f'Cannot verify from {case.status}'}, status=status.HTTP_400_BAD_REQUEST)

    StateMachine.transition(case, 'VERIFYING', triggered_by='system', reason='Awaiting customer verification')

    return Response({'case_id': case.case_id, 'status': case.status})


# ──────────────────────────────────────────────────────────────────────────────
# CUSTOMER CONFIRMS  (Step 5b — customer responds)
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Customer confirms or rejects resolution',
    description=(
        '**Step 5 — Verify (customer side)**\n\n'
        'The customer responds to the proposed resolution:\n'
        '- `confirmed: true` → Case moves to `RESOLVED`\n'
        '- `confirmed: false` → Case moves to `REOPENED` and returns to investigation\n\n'
        'This is the critical feedback loop that prevents dead-end resolutions.\n\n'
        'Valid from: `VERIFYING` only.'
    ),
    request={
        'application/json': {
            'type': 'object',
            'required': ['confirmed'],
            'properties': {
                'confirmed': {'type': 'boolean', 'description': 'true = resolved, false = still a problem'},
                'note': {'type': 'string', 'description': 'Optional note from customer'},
            },
        }
    },
    responses={200: OpenApiResponse(description='Case moved to RESOLVED or REOPENED')},
    tags=['Verification'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def customer_verify_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    data = request.data
    confirmed = data.get('confirmed', True)

    if case.status != 'VERIFYING':
        return Response({'error': f'Cannot verify from {case.status}'}, status=status.HTTP_400_BAD_REQUEST)

    if confirmed:
        StateMachine.transition(case, 'RESOLVED', triggered_by='customer', reason='Customer confirmed resolution')
        case.customer_verified = True
        case.verification_note = data.get('note', '')
        case.save()
    else:
        StateMachine.transition(case, 'REOPENED', triggered_by='customer', reason='Customer says issue persists')
        case.customer_verified = False
        case.save()

    return Response({'case_id': case.case_id, 'status': case.status})


# ──────────────────────────────────────────────────────────────────────────────
# CLOSE CASE  (Step 6 — final state)
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Close case',
    description=(
        '**Step 6 — Closed**\n\n'
        'Closes the case permanently. The full record is now immutable.\n\n'
        'Valid from: `RESOLVED` only.'
    ),
    responses={200: OpenApiResponse(description='Case moved to CLOSED')},
    tags=['Resolution'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def close_case_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    if case.status != 'RESOLVED':
        return Response({'error': f'Cannot close from {case.status}'}, status=status.HTTP_400_BAD_REQUEST)
    StateMachine.transition(case, 'CLOSED', triggered_by='system', reason='Case closed')
    return Response({'case_id': case.case_id, 'status': case.status})


# ──────────────────────────────────────────────────────────────────────────────
# ADD MESSAGE
# ──────────────────────────────────────────────────────────────────────────────
@extend_schema(
    summary='Add a message to a case',
    description=(
        'Adds a message to the case thread. Messages are visible to both the customer and agents.\n\n'
        '- Customer messages: `sender_type: "customer"`\n'
        '- Agent messages: `sender_type: "agent"`'
    ),
    request={
        'application/json': {
            'type': 'object',
            'required': ['text'],
            'properties': {
                'sender': {'type': 'string', 'example': 'Jane Doe'},
                'sender_type': {'type': 'string', 'enum': ['customer', 'agent'], 'default': 'customer'},
                'text': {'type': 'string', 'example': 'Thank you for resolving this'},
            },
        }
    },
    responses={201: OpenApiResponse(description='Message added', examples=[OpenApiExample('Added', value={'message_id': 1})])},
    tags=['Messages'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def add_message_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    data = request.data
    msg = CaseMessage.objects.create(
        case=case,
        sender=data.get('sender', 'Anonymous'),
        sender_type=data.get('sender_type', 'customer'),
        text=data.get('text', ''),
    )
    return Response({'message_id': msg.id}, status=status.HTTP_201_CREATED)
