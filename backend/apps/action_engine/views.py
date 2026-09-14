from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class ActionPlanViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]


class ActionResultViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
