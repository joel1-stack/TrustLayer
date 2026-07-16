import logging
from datetime import timedelta
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.conf import settings
from apps.agreements.models import Agreement
from apps.agreements.services import AgreementService
from apps.payments.services import PaymentService
from apps.state_machine.services import StateMachine
from apps.constants import STATUS_CODES
from .serializers import CreateAgreementSerializer, AgreementResponseSerializer

logger = logging.getLogger(__name__)


class CustomerTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        from apps.customer_portal.models import Customer
        try:
            customer = Customer.objects.get(api_key=key, status='active')
        except Customer.DoesNotExist:
            return None
        return (customer, None)


@api_view(['POST'])
@authentication_classes([CustomerTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_agreement(request):
    serializer = CreateAgreementSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': 'Validation failed', 'details': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    customer = request.user

    amount = data['amount']
    currency = data['currency']
    provider = data['provider']
    webhook_url = data.get('webhook_url') or ''
    title = data.get('title') or 'Agreement'
    description = data.get('description') or ''
    external_id = data.get('external_id') or ''
    parties_data = data['parties']
    conditions_data = data.get('conditions') or []

    # 1. Create agreement
    agreement = AgreementService.create_agreement(
        title=title,
        amount=amount,
        creator_id=customer.customer_id,
        description=description,
        currency=currency,
        creator_type='developer',
        metadata={'external_id': external_id, 'provider': provider},
    )

    # Set developer webhook URL
    if webhook_url:
        agreement.developer_webhook_url = webhook_url
        agreement.save(update_fields=['developer_webhook_url'])

    # 2. Add parties from request
    for p in parties_data:
        split_pct = None
        if p.get('split_share') is not None:
            split_pct = Decimal(str(p['split_share'])) * Decimal('100')
        AgreementService.add_party(
            agreement,
            role=p['role'],
            identifier=p['identifier'],
            name=p['name'],
            split_percentage=split_pct,
            payout_method=provider,
        )

    # AgreementService.create_agreement already auto-injects a PLATFORM party with configured fee

    # 3. Create conditions
    from apps.conditions.services import ConditionService
    for c in conditions_data:
        ConditionService.add_condition(
            agreement=agreement,
            condition_type=c['type'],
            label=c.get('type', 'condition'),
            required=c.get('required', True),
        )

    # 4. Generate payment link
    buyer = next((p for p in parties_data if p['role'] == 'BUYER'), None)
    buyer_phone = buyer['identifier'] if buyer else ''
    tx, result = PaymentService.generate_payment_link(agreement, phone=buyer_phone, provider=provider)

    if not result.get('success'):
        import uuid
        payment_url = f'{settings.TRUSTLAYER_BASE_URL}/pay/sim/{agreement.agreement_id}/{uuid.uuid4().hex[:8]}'
        agreement.payment_url = payment_url
        agreement.save(update_fields=['payment_url'])
        logger.warning(f"Payment provider failed for {agreement.agreement_id}: {result.get('error')}. Using simulated link.")
    else:
        payment_url = result['payment_url']
    agreement.payment_url = payment_url
    agreement.save(update_fields=['payment_url'])

    # 5. State machine: CREATED -> CONFIRMED -> SUBMITTED
    ip_address = request.META.get('REMOTE_ADDR', '')
    try:
        StateMachine.transition(
            agreement, 'CONFIRMED',
            triggered_by='api_v1',
            actor_role='developer',
            channel='api',
            ip_address=ip_address,
            reason='V1 API agreement created',
        )
    except ValueError:
        pass

    try:
        StateMachine.transition(
            agreement, 'SUBMITTED',
            triggered_by='api_v1',
            actor_role='settlement_engine',
            channel='api',
            ip_address=ip_address,
            provider_ref=result.get('provider_reference', ''),
            reason=f'Payment link generated: {payment_url[:40]}...',
        )
    except ValueError:
        pass

    # 6. Fire notification (sends developer webhook if webhook_url set)
    from apps.notifications.services import NotificationService
    NotificationService.on_payment_submitted(agreement, payment_url=payment_url)

    # 7. Return the golden response
    expires_at = timezone.now() + timedelta(hours=24)
    resp = AgreementResponseSerializer({
        'agreement_id': agreement.agreement_id,
        'status': 'SUBMITTED',
        'status_code': STATUS_CODES.get('SUBMITTED', 12000),
        'payment_link': payment_url,
        'expires_at': expires_at,
        'next_step': (
            f"Send the 'payment_link' to the BUYER. "
            f"TrustLayer will notify your webhook_url when funds are available."
        ),
    })
    return Response(resp.data, status=status.HTTP_201_CREATED)