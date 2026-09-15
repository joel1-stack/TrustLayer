from rest_framework import serializers


class CreateCaseSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, help_text='Human-readable problem description')
    intent = serializers.ChoiceField(
        choices=[
            'DATA_FAILURE', 'VOICE_FAILURE', 'SMS_FAILURE',
            'PAYMENT_FAILURE', 'BILLING_DISPUTE', 'ACCOUNT_ISSUE',
            'NETWORK_ISSUE', 'OTHER',
        ],
        help_text='Problem category'
    )
    channel = serializers.ChoiceField(
        choices=['WEB', 'MOBILE', 'API', 'VOICE', 'SMS'],
        default='WEB',
        help_text='Channel where the case was created'
    )
    severity = serializers.ChoiceField(
        choices=['LOW', 'NORMAL', 'HIGH', 'CRITICAL'],
        default='NORMAL',
        help_text='Problem severity'
    )
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    msisdn = serializers.CharField(max_length=20, help_text='Phone number (e.g. +254712345678)')
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    provider = serializers.CharField(required=False, allow_blank=True, max_length=100)
    metadata = serializers.DictField(required=False, default=dict)


class CaseResponseSerializer(serializers.Serializer):
    case_id = serializers.CharField()
    title = serializers.CharField()
    status = serializers.CharField()
    status_code = serializers.IntegerField()
    intent = serializers.CharField()
    severity = serializers.CharField()
    msisdn = serializers.CharField()
    created_at = serializers.CharField()
    message = serializers.CharField()
