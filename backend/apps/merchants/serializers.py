"""
Merchant API Serializers
"""
from rest_framework import serializers
from .models import Merchant, MerchantAPIKey


class MerchantRegisterSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    email        = serializers.EmailField()
    phone        = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        phone = value.strip().replace(' ', '')
        if phone.startswith('07') or phone.startswith('01'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            raise serializers.ValidationError("Phone must start with 254, 07, or 01")
        if len(phone) != 12:
            raise serializers.ValidationError("Phone number must be 12 digits (2547XXXXXXXX)")
        return phone


class MerchantResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Merchant
        fields = [
            'id', 'company_name', 'email', 'phone', 'merchant_key',
            'compliance_status', 'subscription_tier', 'trust_score',
            'total_volume', 'dispute_rate', 'monthly_volume_limit',
            'webhook_url', 'success_url', 'failure_url',
            'created_at', 'updated_at',
        ]


class MerchantUpdateSerializer(serializers.Serializer):
    webhook_url  = serializers.URLField(max_length=500, required=False, allow_blank=True)
    success_url  = serializers.URLField(max_length=500, required=False, allow_blank=True)
    failure_url  = serializers.URLField(max_length=500, required=False, allow_blank=True)
    company_name = serializers.CharField(max_length=255, required=False)
    phone        = serializers.CharField(max_length=20, required=False)
