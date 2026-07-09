from rest_framework import serializers
from .models import Agreement, AgreementParty

class AgreementPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgreementParty
        fields = ['id', 'role', 'identifier', 'name', 'payout_method', 'payout_details', 'split_percentage', 'split_fixed', 'created_at']

class AgreementSerializer(serializers.ModelSerializer):
    parties = AgreementPartySerializer(many=True, read_only=True)

    class Meta:
        model = Agreement
        fields = ['agreement_id', 'status', 'title', 'description', 'amount', 'currency', 'metadata', 'creator_id', 'creator_type', 'created_at', 'updated_at', 'parties']