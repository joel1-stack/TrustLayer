from rest_framework import viewsets, status 
from rest_framework.decorators import action 
from rest_framework.response import Response 
from rest_framework.permissions import IsAuthenticated 
from django.contrib.auth.models import User 
from django.db import transaction 
import uuid 
from .models import Transaction, Wallet 
from .serializers import UserSerializer, TransactionSerializer, WalletSerializer 
 
 
class UserViewSet(viewsets.ModelViewSet): 
    queryset = User.objects.all() 
    serializer_class = UserSerializer 
 
 
class WalletViewSet(viewsets.ModelViewSet): 
    serializer_class = WalletSerializer 
    permission_classes = [IsAuthenticated] 
    def get_queryset(self): 
        return Wallet.objects.filter(user=self.request.user) 
    @action(detail=False, methods=['get']) 
    def my_wallet(self, request): 
        wallet, created = Wallet.objects.get_or_create(user=request.user, defaults={'currency': 'KES'}) 
        serializer = self.get_serializer(wallet) 
        return Response(serializer.data) 
 
 
class TransactionViewSet(viewsets.ModelViewSet): 
    serializer_class = TransactionSerializer 
    permission_classes = [IsAuthenticated] 
    def get_queryset(self): 
        return Transaction.objects.filter(user=self.request.user) 
    def perform_create(self, serializer): 
        reference = f"TXN-{uuid.uuid4().hex[:12].upper()}" 
        serializer.save(user=self.request.user, reference=reference) 
    @action(detail=True, methods=['post']) 
    def complete(self, request, pk=None): 
        with transaction.atomic(): 
            txn = self.get_object() 
            if txn.status != 'pending': 
                return Response({'error': 'Transaction already processed'}, status=status.HTTP_400_BAD_REQUEST) 
            txn.status = 'completed' 
            txn.save() 
            wallet, _ = Wallet.objects.get_or_create(user=txn.user) 
            wallet.balance += txn.amount 
            wallet.save() 
            return Response({'status': 'Transaction completed'}) 
