import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import DeveloperAgreementSerializer
from apps.agreements.services import create_and_initiate_agreement

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_agreement_api(request):
    serializer = DeveloperAgreementSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = create_and_initiate_agreement(
            validated_data=serializer.validated_data,
            api_user=request.user,
        )

        return Response({
            "agreement_id": result['agreement_id'],
            "status": "SUBMITTED",
            "status_code": 12000,
            "payment_link": result['payment_link'],
            "next_step": "Send the payment_link to the BUYER to complete payment.",
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception("Agreement creation failed")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
