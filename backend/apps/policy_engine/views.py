from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class PolicyRuleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]


class PolicyDecisionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
