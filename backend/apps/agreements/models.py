from django.db import models
from apps.core.constants import STATUS_CODES, STATUS_CATEGORIES


class Case(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        EVIDENCE_COLLECTION = 'EVIDENCE_COLLECTION', 'Evidence Collection'
        INVESTIGATING = 'INVESTIGATING', 'Investigating'
        RESOLUTION_RECORDED = 'RESOLUTION_RECORDED', 'Resolution Recorded'
        ESCALATED = 'ESCALATED', 'Escalated'
        VERIFYING = 'VERIFYING', 'Verifying'
        RESOLVED = 'RESOLVED', 'Resolved'
        REOPENED = 'REOPENED', 'Reopened'
        CLOSED = 'CLOSED', 'Closed'

    case_id = models.CharField(max_length=24, unique=True, editable=False, db_column='agreement_id')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN)
    status_code_value = models.IntegerField(default=10000, db_index=True)

    # Problem
    problem_type = models.CharField(max_length=50, default='TRANSACTION_DISPUTE')
    txn_id = models.CharField(max_length=100, blank=True, default='')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='KES')
    description = models.TextField(blank=True, default='')
    date_occurred = models.DateField(null=True, blank=True)

    # Customer
    customer_name = models.CharField(max_length=255, blank=True, default='')
    customer_email = models.CharField(max_length=255, blank=True, default='')
    customer_phone = models.CharField(max_length=50, blank=True, default='')

    # Routing
    assigned_team = models.CharField(max_length=100, default='FRAUD_OPERATIONS')
    priority = models.CharField(max_length=20, default='NORMAL', help_text="LOW, NORMAL, HIGH, CRITICAL")

    # Investigation
    investigation_notes = models.TextField(blank=True, default='')
    finding = models.CharField(max_length=255, blank=True, default='')

    # Resolution
    resolution_type = models.CharField(max_length=50, blank=True, default='')
    resolution_note = models.TextField(blank=True, default='')
    resolved_by = models.CharField(max_length=100, blank=True, default='')

    # Verification
    customer_verified = models.BooleanField(default=False)
    verification_note = models.TextField(blank=True, default='')

    # Meta
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agreements'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.case_id:
            import secrets, string
            self.case_id = 'CASE' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        if not self.status_code_value or self.status_code_value == 10000:
            self.status_code_value = STATUS_CODES.get(self.status, 10000)
        super().save(*args, **kwargs)

    @property
    def status_code(self):
        return self.status_code_value or STATUS_CODES.get(self.status, 0)

    @property
    def status_category(self):
        return STATUS_CATEGORIES.get(self.status, 'active')

    def __str__(self):
        return f"{self.case_id} [{self.status}] {self.description[:50]}"

    @property
    def agreement_id(self):
        return self.case_id

    @property
    def contact(self):
        return self.customer_phone or self.customer_email or '—'

    @property
    def transaction_ref(self):
        return self.txn_id

    @property
    def incident_date(self):
        return self.date_occurred

    @property
    def resolution_title(self):
        from apps.agreements.case_flow import RESOLUTION_LABELS
        return RESOLUTION_LABELS.get(self.resolution_type, self.finding or self.resolution_type or 'Resolution recorded')

    @property
    def provider_action(self):
        return (self.metadata or {}).get('provider_action', '')

    @property
    def badge_class(self):
        return {
            'OPEN': 'open',
            'EVIDENCE_COLLECTION': 'evidence',
            'INVESTIGATING': 'investigating',
            'RESOLUTION_RECORDED': 'resolution',
            'ESCALATED': 'escalated',
            'VERIFYING': 'verifying',
            'RESOLVED': 'resolved',
            'REOPENED': 'reopened',
            'CLOSED': 'closed',
        }.get(self.status, 'open')

    @property
    def problem_label(self):
        return {
            'TRANSACTION_DISPUTE': 'Transaction not recognized',
            'PAYMENT_PROBLEM': 'Payment problem',
            'ACCOUNT_PROBLEM': 'Account security',
            'OTHER': 'Other issue',
        }.get(self.problem_type, self.problem_type.replace('_', ' ').title())


class CaseMessage(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=100)
    sender_type = models.CharField(max_length=20, default='customer')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'case_messages'
        ordering = ['created_at']


class CaseEvidence(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='evidence_items')
    evidence_type = models.CharField(max_length=50, default='screenshot')
    url = models.URLField(blank=True, default='')
    filename = models.CharField(max_length=255, blank=True, default='')
    description = models.CharField(max_length=500, blank=True, default='')
    uploaded_by = models.CharField(max_length=100, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'case_evidence'
        ordering = ['-created_at']


class CaseTimeline(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='timeline')
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    reason = models.CharField(max_length=500, blank=True, default='')
    triggered_by = models.CharField(max_length=100, default='system')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'case_timeline'
        ordering = ['created_at']
