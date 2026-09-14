from rest_framework import serializers


class PartySerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[
        'BUYER', 'VENDOR', 'DELIVERY_AGENT', 'PLATFORM',
        'SELLER', 'MARKETPLACE', 'CUSTOMER', 'PARTNER', 'AGENT'])
    name = serializers.CharField(max_length=255)
    identifier = serializers.CharField(max_length=128, help_text='Phone or email')
    split_share = serializers.FloatField(required=False, min_value=0, max_value=1,
                                         help_text='Fraction of total (e.g. 0.93 for 93%%)')


class ConditionSerializer(serializers.Serializer):
    condition_type = serializers.ChoiceField(choices=[
        'custom_webhook', 'delivery_confirmation', 'inspection', 'time_based',
        'document_upload', 'manual_review', 'payment_confirmation'])
    triggered_by = serializers.CharField(required=False, max_length=64,
                                         help_text='Party role that triggers this condition')
    required = serializers.BooleanField(default=True)


class DeveloperAgreementSerializer(serializers.Serializer):
    external_id = serializers.CharField(required=False, allow_null=True, max_length=255,
                                        help_text='Your internal reference (e.g. ORDER_123)')
    title = serializers.CharField(default='API Agreement', max_length=255,
                                  help_text='Human-readable agreement title')
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000,
                                        help_text='Optional description')
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(default='KES', max_length=3)
    provider = serializers.CharField(default='mpesa')
    webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True,
                                       help_text='TrustLayer will POST state changes here')
    parties = PartySerializer(many=True)
    conditions = ConditionSerializer(many=True, required=False)
