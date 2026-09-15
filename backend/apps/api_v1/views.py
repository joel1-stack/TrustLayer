from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.agreements.models import Case, CaseMessage, CaseEvidence
from apps.agreements import case_flow
from apps.state_machine.services import StateMachine


@api_view(['GET'])
@permission_classes([AllowAny])
def list_cases_api(request):
    cases = Case.objects.all()[:50]
    data = []
    for c in cases:
        data.append({
            'case_id': c.case_id,
            'status': c.status,
            'problem_type': c.problem_type,
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
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_case_api(request):
    data = request.data
    description = data.get('description', '')
    if not description:
        return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)
    case = case_flow.create_case_from_request(data)
    return Response({
        'case_id': case.case_id,
        'status': case.status,
        'assigned_team': case.assigned_team,
        'priority': case.priority,
        'message': f'Case {case.case_id} created.'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def case_detail_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)

    timeline = CaseTimeline.objects.filter(case=case).order_by('created_at')
    messages = CaseMessage.objects.filter(case=case).order_by('created_at')
    evidence = CaseEvidence.objects.filter(case=case).order_by('-created_at')

    return Response({
        'case_id': case.case_id,
        'status': case.status,
        'status_code': case.status_code,
        'problem_type': case.problem_type,
        'txn_id': case.txn_id,
        'amount': str(case.amount),
        'currency': case.currency,
        'description': case.description,
        'date_occurred': case.date_occurred.isoformat() if case.date_occurred else None,
        'customer_name': case.customer_name,
        'customer_email': case.customer_email,
        'customer_phone': case.customer_phone,
        'priority': case.priority,
        'assigned_team': case.assigned_team,
        'investigation_notes': case.investigation_notes,
        'finding': case.finding,
        'resolution_type': case.resolution_type,
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
    })


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


@api_view(['POST'])
@permission_classes([AllowAny])
def start_investigation_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    agent_id = request.data.get('agent_id', 'agent')

    if case.status in ['OPEN', 'EVIDENCE_COLLECTION']:
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=agent_id, reason='Agent started investigation')

    return Response({'status': case.status})


@api_view(['POST'])
@permission_classes([AllowAny])
def resolve_case_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    data = request.data

    if case.status not in ['INVESTIGATING', 'ESCALATED', 'OPEN', 'EVIDENCE_COLLECTION']:
        return Response({'error': f'Cannot resolve from {case.status}'}, status=status.HTTP_400_BAD_REQUEST)

    if case.status in ['OPEN', 'EVIDENCE_COLLECTION']:
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=data.get('agent_id', 'agent'), reason='Agent picked up')
    if case.status == 'ESCALATED':
        StateMachine.transition(case, 'INVESTIGATING', triggered_by=data.get('agent_id', 'agent'), reason='Escalation addressed')

    StateMachine.transition(case, 'RESOLUTION_RECORDED', triggered_by=data.get('agent_id', 'agent'), reason='Resolution recorded')

    case.resolution_type = data.get('resolution_type', '')
    case.resolution_note = data.get('note', '')
    case.resolved_by = data.get('agent_id', 'agent')
    case.finding = data.get('finding', '')
    case.save()

    return Response({'case_id': case.case_id, 'status': case.status})


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_case_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)

    if case.status != 'RESOLUTION_RECORDED':
        return Response({'error': f'Cannot verify from {case.status}'}, status=status.HTTP_400_BAD_REQUEST)

    StateMachine.transition(case, 'VERIFYING', triggered_by='system', reason='Awaiting customer verification')

    return Response({'case_id': case.case_id, 'status': case.status})


@api_view(['POST'])
@permission_classes([AllowAny])
def customer_verify_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    data = request.data
    confirmed = data.get('confirmed', True)

    if case.status not in ['VERIFYING', 'RESOLUTION_RECORDED']:
        return Response({'error': f'Cannot verify from {case.status}'}, status=status.HTTP_400_BAD_REQUEST)

    case_flow.apply_customer_verification(case, bool(confirmed), note=data.get('note', ''))
    case.refresh_from_db()
    return Response({'case_id': case.case_id, 'status': case.status})


@api_view(['POST'])
@permission_classes([AllowAny])
def close_case_api(request, case_id):
    case = get_object_or_404(Case, case_id=case_id)
    if case.status != 'RESOLVED':
        return Response({'error': f'Cannot close from {case.status}'}, status=status.HTTP_400_BAD_REQUEST)
    StateMachine.transition(case, 'CLOSED', triggered_by='system', reason='Case closed')
    return Response({'case_id': case.case_id, 'status': case.status})


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
