from rest_framework import serializers
from .models import Agreement, AgreementParty

class AgreementPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgreementParty
        fields = ['id', 'role', 'name', 'identifier', 'payout_method', 'split_percentage']

class AgreementSerializer(serializers.ModelSerializer):
    parties = AgreementPartySerializer(many=True, read_only=True)

    class Meta:
        model = Agreement
        fields = ['agreement_id', 'status', 'title', 'amount', 'currency', 'creator_id', 'created_at', 'updated_at', 'parties']