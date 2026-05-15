import uuid
from django.db import models


class Dispute(models.Model):
    STATUS_CHOICES = [
        ('OPEN',              'Open'),
        ('EVIDENCE_SUBMITTED','Evidence Submitted'),
        ('UNDER_REVIEW',      'Under Review'),
        ('RESOLVED_BUYER',    'Resolved — Buyer Wins'),
        ('RESOLVED_SELLER',   'Resolved — Seller Wins'),
        ('CLOSED',            'Closed'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deal       = models.OneToOneField('escrow.EscrowDeal', on_delete=models.CASCADE, related_name='dispute')
    opened_by  = models.CharField(max_length=10, choices=[('BUYER','Buyer'),('SELLER','Seller')])
    reason     = models.TextField()
    status     = models.CharField(max_length=30, choices=STATUS_CHOICES, default='OPEN')

    buyer_evidence       = models.TextField(blank=True)
    seller_evidence      = models.TextField(blank=True)
    buyer_evidence_files = models.JSONField(default=list, blank=True)
    seller_evidence_files= models.JSONField(default=list, blank=True)

    resolution_notes = models.TextField(blank=True)
    penalty_amount   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    penalty_to       = models.CharField(max_length=10, blank=True)

    assigned_admin    = models.CharField(max_length=100, blank=True)
    opened_at         = models.DateTimeField(auto_now_add=True)
    evidence_deadline = models.DateTimeField(null=True, blank=True)
    resolved_at       = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'disputes'
        ordering = ['-opened_at']

    def __str__(self):
        return f"Dispute {self.id} — {self.status}"


class DisputeMessage(models.Model):
    dispute    = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='messages')
    sender     = models.CharField(max_length=10, choices=[('BUYER','Buyer'),('SELLER','Seller'),('ADMIN','Admin')])
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dispute_messages'
        ordering = ['created_at']
