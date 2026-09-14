from decimal import Decimal
from django.conf import settings
from django.db import transaction
from .models import Case, CaseParty


class CaseService:

    @staticmethod
    def create_agreement(title, amount, creator_id, description='', currency='KES', creator_type='organization', metadata=None):
        agreement = Case.objects.create(
            title=title,
            amount=amount,
            currency=currency,
            creator_id=creator_id,
            creator_type=creator_type,
            description=description,
            metadata=metadata or {},
        )
        # Auto-inject platform party with configured fee + phone
        CaseService.add_party(
            agreement,
            role='PLATFORM',
            identifier=settings.TRUSTLAYER_PLATFORM_PHONE,
            name='TrustLayer Platform',
            split_percentage=settings.TRUSTLAYER_PLATFORM_FEE_PERCENT,
            payout_method='mpesa',
        )
        return agreement

    @staticmethod
    def add_party(agreement, role, identifier, name, split_percentage=None, split_fixed=None, payout_method='', payout_details=None):
        party = CaseParty.objects.create(
            agreement=agreement,
            role=role,
            identifier=identifier,
            name=name,
            payout_method=payout_method,
            split_percentage=split_percentage,
            split_fixed=split_fixed,
            payout_details=payout_details or {},
        )
        return party

    @staticmethod
    def calculate_splits(agreement):
        parties = agreement.parties.all()
        total_pct = sum(p.split_percentage or 0 for p in parties)
        total_fixed = sum(p.split_fixed or 0 for p in parties)

        splits = []
        assigned_amount = Decimal('0.00')
        remainder_recipient = None

        for p in parties:
            amount = Decimal('0.00')
            if p.split_percentage:
                amount += (agreement.amount * p.split_percentage / Decimal('100.00')).quantize(Decimal('0.01'))
            if p.split_fixed:
                amount += p.split_fixed
            if p.split_percentage or p.split_fixed:
                assigned_amount += amount
                splits.append({'party': p, 'amount': amount})
            else:
                remainder_recipient = p

        if remainder_recipient:
            remainder = agreement.amount - assigned_amount
            if remainder > 0:
                splits.append({'party': remainder_recipient, 'amount': remainder})

        return splits

    @staticmethod
    def get_agreement(agreement_id):
        return Case.objects.filter(agreement_id=agreement_id).first()


def create_and_initiate_agreement(validated_data, api_user):
    with transaction.atomic():
        metadata = {}
        external_id = validated_data.get('external_id', '')
        if external_id:
            metadata['external_id'] = external_id
        provider = validated_data.get('provider', 'mpesa')
        if provider:
            metadata['provider'] = provider

        agreement = Case.objects.create(
            title=validated_data.get('title', 'API Agreement'),
            amount=validated_data['amount'],
            description=validated_data.get('description', ''),
            currency=validated_data.get('currency', 'KES'),
            developer_webhook_url=validated_data.get('webhook_url', ''),
            creator_id=api_user.username if api_user else 'system',
            creator_type='developer',
            metadata=metadata,
        )

        from apps.state_machine.services import StateMachine
        StateMachine.transition(
            agreement, 'CONFIRMED',
            actor_role='SYSTEM', channel='API',
            reason='Valid payload from developer API'
        )

        for party_data in validated_data['parties']:
            split_share = party_data.get('split_share')
            split_pct = None
            if split_share is not None:
                split_pct = Decimal(str(split_share)) * Decimal('100')

            CaseParty.objects.create(
                agreement=agreement,
                role=party_data['role'],
                name=party_data.get('name', ''),
                identifier=party_data['identifier'],
                split_percentage=split_pct,
                payout_method=provider,
            )

        has_platform = any(p['role'] == 'PLATFORM' for p in validated_data['parties'])
        if not has_platform:
            CaseParty.objects.create(
                agreement=agreement,
                role='PLATFORM',
                name='TrustLayer Platform',
                identifier=settings.TRUSTLAYER_PLATFORM_PHONE,
                split_percentage=settings.TRUSTLAYER_PLATFORM_FEE_PERCENT,
                payout_method=provider,
            )

        for cond_data in validated_data.get('conditions', []):
            from apps.conditions.models import Condition
            Condition.objects.create(
                agreement=agreement,
                condition_type=cond_data.get('type', cond_data.get('condition_type', 'custom_webhook')),
                required=cond_data.get('required', True),
                label=cond_data.get('type', cond_data.get('condition_type', 'condition')),
            )

        buyer = next(
            (p for p in validated_data['parties'] if p['role'] == 'BUYER'),
            None
        )
        buyer_phone = buyer['identifier'] if buyer else ''

        from apps.payments.adapters.registry import get_adapter
        adapter = get_adapter(provider)
        provider_response = adapter.generate_link(
            amount=float(agreement.amount),
            phone=buyer_phone,
            reference=agreement.agreement_id,
            currency=agreement.currency,
            webhook_url=validated_data.get('webhook_url', ''),
        )

        provider_ref = provider_response.get('provider_reference', '')
        agreement.payment_url = provider_response.get('payment_url', '')
        agreement.save(update_fields=['payment_url', 'updated_at'])

        StateMachine.transition(
            agreement, 'SUBMITTED',
            actor_role='SETTLEMENT_ENGINE', channel='API',
            reason='Payment link generated via provider',
            provider_ref=provider_ref,
        )

        if agreement.developer_webhook_url:
            from apps.notifications.services import NotificationService
            NotificationService.on_payment_submitted(
                agreement,
                payment_url=agreement.payment_url,
            )

        return {
            'agreement_id': agreement.agreement_id,
            'payment_link': agreement.payment_url,
        }


AgreementService = CaseService