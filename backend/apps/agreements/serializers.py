from rest_framework import serializers
from .models import Agreement, AgreementParty

class AgreementPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgreementParty
        fields = ['id', 'role', 'name', 'identifier', 'payout_method', 'split_percentage']

class AgreementSerializer(serializers.ModelSerializer):
    parties = AgreementPartySerializer(many=True, read_only=True)
    status_code = serializers.SerializerMethodField()

    class Meta:
        model = Agreement
        fields = ['agreement_id', 'status', 'status_code', 'title', 'amount', 'currency', 'creator_id', 'created_at', 'updated_at', 'parties']

    def get_status_code(self, obj):
        return obj.status_code
