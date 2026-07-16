from rest_framework import serializers
from apps.agreements.models import Agreement


class PartySerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[
        'BUYER', 'VENDOR', 'DELIVERY_AGENT', 'PLATFORM',
        'SELLER', 'MARKETPLACE', 'CUSTOMER', 'PARTNER', 'AGENT'])
    name = serializers.CharField(max_length=255)
    identifier = serializers.CharField(max_length=128, help_text='Phone or email')
    split_share = serializers.FloatField(required=False, min_value=0, max_value=1,
                                         help_text='Fraction of total (e.g. 0.93 for 93%%)')


class ConditionSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['custom_webhook', 'delivery_confirmation', 'inspection', 'time_based',
                                            'document_upload', 'manual_review', 'payment_confirmation'])
    triggered_by = serializers.CharField(required=False, max_length=64,
                                         help_text='Party role that triggers this condition')
    required = serializers.BooleanField(default=True)


class CreateAgreementSerializer(serializers.Serializer):
    external_id = serializers.CharField(required=False, max_length=255,
                                        help_text='Your internal reference (e.g. ORDER_123)')
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(default='KES', max_length=3)
    provider = serializers.ChoiceField(choices=['intasend', 'mpesa', 'stripe'], default='intasend')
    webhook_url = serializers.URLField(required=False, default='',
                                       help_text='TrustLayer will POST state changes here')
    title = serializers.CharField(default='Agreement', max_length=255)
    description = serializers.CharField(default='', allow_blank=True)
    parties = PartySerializer(many=True, min_length=1)
    conditions = ConditionSerializer(many=True, required=False, default=[])

    def validate_parties(self, value):
        roles = [p['role'] for p in value]
        if 'BUYER' not in roles:
            raise serializers.ValidationError('At least one party must have role BUYER')
        return value

    def validate(self, data):
        total_share = sum(p.get('split_share') or 0 for p in data['parties'])
        has_platform = any(p['role'] == 'PLATFORM' for p in data['parties'])
        if not has_platform and total_share >= 1:
            raise serializers.ValidationError(
                'Total split shares must be less than 1 when no PLATFORM party is included '
                '(platform fee will be auto-added)')
        if has_platform and total_share != 1:
            raise serializers.ValidationError(
                f'Total split shares must equal 1 when PLATFORM party is specified (got {total_share})')
        return data


class AgreementResponseSerializer(serializers.Serializer):
    agreement_id = serializers.CharField()
    status = serializers.CharField()
    status_code = serializers.IntegerField()
    payment_link = serializers.URLField()
    expires_at = serializers.DateTimeField(required=False)
    next_step = serializers.CharField()