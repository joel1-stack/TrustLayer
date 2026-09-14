from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class VerificationCheckViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]


class VerificationResultViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
