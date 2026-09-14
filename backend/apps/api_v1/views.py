import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import DeveloperAgreementSerializer
from apps.agreements.services import create_and_initiate_agreement
from apps.agreements.models import Case

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_cases_api(request):
    qs = Case.objects.all().order_by('-created_at')[:100]
    data = []
    for c in qs:
        data.append({
            'case_id': c.agreement_id,
            'title': c.title,
            'status': c.status,
            'status_code': c.status_code,
            'amount': str(c.amount),
            'currency': c.currency,
            'created_at': c.created_at.isoformat(),
        })
    return Response({'cases': data, 'count': len(data)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_detail_api(request, case_id):
    try:
        c = Case.objects.get(agreement_id=case_id)
    except Case.DoesNotExist:
        return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    parties = []
    for p in c.parties.all():
        parties.append({
            'role': p.role,
            'name': p.name,
            'identifier': p.identifier,
        })

    return Response({
        'case_id': c.agreement_id,
        'title': c.title,
        'status': c.status,
        'status_code': c.status_code,
        'amount': str(c.amount),
        'currency': c.currency,
        'parties': parties,
        'created_at': c.created_at.isoformat(),
        'updated_at': c.updated_at.isoformat(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_case_api(request):
    serializer = DeveloperAgreementSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = create_and_initiate_agreement(
            validated_data=serializer.validated_data,
            api_user=request.user,
        )

        return Response({
            "case_id": result['agreement_id'],
            "status": "SUBMITTED",
            "status_code": 12000,
            "payment_link": result['payment_link'],
            "next_step": "Send the payment_link to the BUYER to complete payment.",
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception("Case creation failed")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
