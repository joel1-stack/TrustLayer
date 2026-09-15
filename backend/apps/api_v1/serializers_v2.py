from rest_framework import serializers


class CreateCaseSerializer(serializers.Serializer):
    organization = serializers.SlugField(
        max_length=50,
        help_text='Organization slug: kcb, safaricom, equity, airtel, jumia'
    )
    title = serializers.CharField(max_length=255, help_text='Human-readable problem description')
    intent = serializers.CharField(
        max_length=50,
        help_text='Case type: FRAUD_REPORT, DATA_FAILURE, ORDER_NOT_RECEIVED, etc.'
    )
    customer_ref = serializers.CharField(
        max_length=128, required=False, allow_blank=True,
        help_text='Your internal customer reference (account number, user ID, etc.)'
    )
    channel = serializers.ChoiceField(
        choices=['WEB', 'MOBILE', 'API', 'VOICE', 'SMS', 'WIDGET'],
        default='API',
        help_text='Entry channel'
    )
    severity = serializers.ChoiceField(
        choices=['LOW', 'NORMAL', 'HIGH', 'CRITICAL'],
        default='NORMAL',
        help_text='Problem severity'
    )
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    msisdn = serializers.CharField(required=False, allow_blank=True, max_length=20, help_text='Phone number (optional)')
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    metadata = serializers.DictField(required=False, default=dict)


class CaseResponseSerializer(serializers.Serializer):
    case_id = serializers.CharField()
    title = serializers.CharField()
    status = serializers.CharField()
    status_code = serializers.IntegerField()
    organization = serializers.CharField()
    intent = serializers.CharField()
    severity = serializers.CharField()
    customer_ref = serializers.CharField()
    created_at = serializers.CharField()
    message = serializers.CharField()
