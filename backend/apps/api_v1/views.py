from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.agreements.models import Case, CaseTimeline
from apps.state_machine.services import StateMachine


@api_view(['GET'])
@permission_classes([AllowAny])
def list_cases_api(request):
    """List all cases."""
    cases = Case.objects.all()[:50]
    data = []
    for c in cases:
        data.append({
            'case_id': c.case_id,
            'status': c.status,
            'status_code': c.status_code,
            'description': c.description,
            'txn_id': c.txn_id,
            'amount': str(c.amount),
            'currency': c.currency,
            'customer_name': c.customer_name,
            'severity': c.severity,
            'assigned_team': c.assigned_team,
            'resolution': c.resolution,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None,
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_case_api(request):
    """Create a new dispute case."""
    data = request.data

    txn_id = data.get('txn_id', '')
    amount = data.get('amount', 0)
    description = data.get('description', '')
    customer_name = data.get('customer_name', '')
    customer_email = data.get('customer_email', '')
    customer_phone = data.get('customer_phone', '')
    evidence_url = data.get('evidence_url', '')
    severity = data.get('severity', 'NORMAL')

    if not description:
        return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)

    case = Case.objects.create(
        txn_id=txn_id,
        amount=amount,
        description=description,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        evidence_url=evidence_url,
        severity=severity,
        status='OPEN',
        status_code_value=10000,
    )

    CaseTimeline.objects.create(
        case=case,
        from_status='',
        to_status='OPEN',
        reason='Case created',
        triggered_by='customer',
    )

    return Response({
        'case_id': case.case_id,
        'status': case.status,
        'status_code': case.status_code,
        'message': f'Case {case.case_id} created. Status: OPEN.'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def case_detail_api(request, case_id):
    """Get case detail with timeline and evidence."""
    case = get_object_or_404(Case, case_id=case_id)

    timeline = CaseTimeline.objects.filter(case=case).order_by('created_at')
    timeline_data = [{
        'from_status': t.from_status,
        'to_status': t.to_status,
        'reason': t.reason,
        'triggered_by': t.triggered_by,
        'created_at': t.created_at.isoformat() if t.created_at else None,
    } for t in timeline]

    messages = case.messages.all().order_by('created_at')
    messages_data = [{
        'sender': m.sender,
        'sender_type': m.sender_type,
        'text': m.text,
        'created_at': m.created_at.isoformat() if m.created_at else None,
    } for m in messages]

    evidence = case.evidence_items.all().order_by('-created_at')
    evidence_data = [{
        'evidence_type': e.evidence_type,
        'url': e.url,
        'filename': e.filename,
        'description': e.description,
        'uploaded_by': e.uploaded_by,
        'created_at': e.created_at.isoformat() if e.created_at else None,
    } for e in evidence]

    return Response({
        'case_id': case.case_id,
        'status': case.status,
        'status_code': case.status_code,
        'txn_id': case.txn_id,
        'amount': str(case.amount),
        'currency': case.currency,
        'description': case.description,
        'evidence_url': case.evidence_url,
        'customer_name': case.customer_name,
        'customer_email': case.customer_email,
        'customer_phone': case.customer_phone,
        'severity': case.severity,
        'assigned_team': case.assigned_team,
        'resolution': case.resolution,
        'resolution_note': case.resolution_note,
        'resolved_by': case.resolved_by,
        'created_at': case.created_at.isoformat() if case.created_at else None,
        'updated_at': case.updated_at.isoformat() if case.updated_at else None,
        'timeline': timeline_data,
        'messages': messages_data,
        'evidence': evidence_data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def resolve_case_api(request, case_id):
    """Resolve a case (agent action)."""
    case = get_object_or_404(Case, case_id=case_id)

    if case.status not in ['OPEN', 'INVESTIGATING']:
        return Response({
            'error': f'Case is {case.status}. Can only resolve OPEN or INVESTIGATING cases.'
        }, status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    resolution = data.get('resolution', 'RESOLVED')
    note = data.get('note', '')
    agent_id = data.get('agent_id', 'agent')

    # Transition to INVESTIGATING first if still OPEN
    if case.status == 'OPEN':
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_id, reason='Agent picked up case')

    # Resolve
    StateMachine.transition(case, 'RESOLVED', triggered_by=agent_id, reason=note or 'Case resolved')

    case.resolution = resolution
    case.resolution_note = note
    case.resolved_by = agent_id
    case.save(update_fields=['resolution', 'resolution_note', 'resolved_by', 'updated_at'])

    return Response({
        'case_id': case.case_id,
        'status': case.status,
        'status_code': case.status_code,
        'resolution': case.resolution,
        'message': f'Case {case.case_id} resolved.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def close_case_api(request, case_id):
    """Close a resolved case (customer confirms)."""
    case = get_object_or_404(Case, case_id=case_id)

    if case.status != 'RESOLVED':
        return Response({
            'error': f'Case is {case.status}. Can only close RESOLVED cases.'
        }, status=status.HTTP_400_BAD_REQUEST)

    StateMachine.transition(case, 'CLOSED', triggered_by='customer', reason='Customer confirmed resolution')

    return Response({
        'case_id': case.case_id,
        'status': case.status,
        'message': f'Case {case.case_id} closed.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def add_message_api(request, case_id):
    """Add a message to a case."""
    case = get_object_or_404(Case, case_id=case_id)
    data = request.data

    from apps.agreements.models import CaseMessage
    msg = CaseMessage.objects.create(
        case=case,
        sender=data.get('sender', 'Anonymous'),
        sender_type=data.get('sender_type', 'customer'),
        text=data.get('text', ''),
    )

    return Response({
        'message_id': msg.id,
        'created_at': msg.created_at.isoformat() if msg.created_at else None,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_evidence_api(request, case_id):
    """Add evidence to a case."""
    case = get_object_or_404(Case, case_id=case_id)
    data = request.data

    from apps.agreements.models import CaseEvidence
    ev = CaseEvidence.objects.create(
        case=case,
        evidence_type=data.get('evidence_type', 'screenshot'),
        url=data.get('url', ''),
        filename=data.get('filename', ''),
        description=data.get('description', ''),
        uploaded_by=data.get('uploaded_by', 'customer'),
    )

    return Response({
        'evidence_id': ev.id,
        'created_at': ev.created_at.isoformat() if ev.created_at else None,
    }, status=status.HTTP_201_CREATED)
