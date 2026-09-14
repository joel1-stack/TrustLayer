from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class EnterpriseAdapterViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
