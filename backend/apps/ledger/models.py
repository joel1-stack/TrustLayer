from django.db import models

class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        DEBIT = 'DEBIT', 'Debit'
        CREDIT = 'CREDIT', 'Credit'
    
    entry_id = models.CharField(max_length=24, unique=True, editable=False)
    agreement = models.ForeignKey('agreements.Agreement', on_delete=models.CASCADE, related_name='ledger_entries')
    entry_type = models.CharField(max_length=6, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reference = models.CharField(max_length=128, blank=True, default='', help_text='Transaction ref, receipt no, etc')
    description = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    
    # Who
    party = models.ForeignKey('agreements.AgreementParty', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ledger_entries'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.entry_id:
            import secrets, string
            self.entry_id = 'LED' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.entry_id} {self.entry_type} {self.amount} [{self.agreement.agreement_id}]"


class LedgerAccount(models.Model):
    """Running balance for each agreement-party combination."""
    party = models.OneToOneField('agreements.AgreementParty', on_delete=models.CASCADE, related_name='ledger_account')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='KES')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ledger_accounts'
    
    def __str__(self):
        return f"{self.party.name}: {self.balance} {self.currency}"
