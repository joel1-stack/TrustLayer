from decimal import Decimal
from .models import LedgerEntry, LedgerAccount

class LedgerService:
    
    @staticmethod
    def credit(agreement, amount, party=None, reference='', description='', metadata=None, currency='KES'):
        if party:
            account, _ = LedgerAccount.objects.get_or_create(party=party, defaults={'currency': currency})
            balance_before = account.balance
            account.balance += amount
            account.save(update_fields=['balance'])
            balance_after = account.balance
        else:
            balance_before = Decimal('0.00')
            balance_after = amount
        
        entry = LedgerEntry.objects.create(
            agreement=agreement,
            entry_type='CREDIT',
            amount=amount,
            currency=currency,
            balance_before=balance_before,
            balance_after=balance_after,
            reference=reference,
            description=description,
            metadata=metadata or {},
            party=party,
        )
        return entry
    
    @staticmethod
    def debit(agreement, amount, party=None, reference='', description='', metadata=None, currency='KES'):
        if party:
            account, _ = LedgerAccount.objects.get_or_create(party=party, defaults={'currency': currency})
            balance_before = account.balance
            account.balance -= amount
            account.save(update_fields=['balance'])
            balance_after = account.balance
        else:
            balance_before = Decimal('0.00')
            balance_after = -amount
        
        entry = LedgerEntry.objects.create(
            agreement=agreement,
            entry_type='DEBIT',
            amount=amount,
            currency=currency,
            balance_before=balance_before,
            balance_after=balance_after,
            reference=reference,
            description=description,
            metadata=metadata or {},
            party=party,
        )
        return entry
    
    @staticmethod
    def get_balance(party):
        account = LedgerAccount.objects.filter(party=party).first()
        return account.balance if account else Decimal('0.00')
    
    @staticmethod
    def get_entries(agreement):
        return LedgerEntry.objects.filter(agreement=agreement)
