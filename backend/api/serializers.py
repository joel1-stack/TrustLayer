from rest_framework import serializers 
from django.contrib.auth.models import User 
from .models import Transaction, Wallet 
 
 
class UserSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = User 
        fields = ['id', 'username', 'email', 'first_name', 'last_name'] 
 
 
class TransactionSerializer(serializers.ModelSerializer): 
    user = UserSerializer(read_only=True) 
    class Meta: 
        model = Transaction 
        fields = '__all__' 
        read_only_fields = ['reference', 'created_at', 'updated_at'] 
 
 
class WalletSerializer(serializers.ModelSerializer): 
    user = UserSerializer(read_only=True) 
    class Meta: 
        model = Wallet 
        fields = '__all__' 
        read_only_fields = ['created_at', 'updated_at'] 
