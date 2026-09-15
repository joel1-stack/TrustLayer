from django.db import models
from apps.core.constants import STATUS_CODES, STATUS_CATEGORIES


class Case(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        INVESTIGATING = 'INVESTIGATING', 'Investigating'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    case_id = models.CharField(max_length=24, unique=True, editable=False, db_column='agreement_id')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    status_code_value = models.IntegerField(default=10000, db_index=True)

    # The problem
    txn_id = models.CharField(max_length=100, blank=True, default='', help_text="Transaction reference number")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='KES')
    description = models.TextField(blank=True, default='')
    evidence_url = models.URLField(blank=True, default='', help_text="Screenshot or evidence URL")

    # Who
    customer_name = models.CharField(max_length=255, blank=True, default='')
    customer_email = models.CharField(max_length=255, blank=True, default='')
    customer_phone = models.CharField(max_length=50, blank=True, default='')
    assigned_team = models.CharField(max_length=100, default='FRAUD_TEAM')

    # Resolution
    resolution = models.CharField(max_length=255, blank=True, default='')
    resolution_note = models.TextField(blank=True, default='')
    resolved_by = models.CharField(max_length=100, blank=True, default='')

    # Meta
    severity = models.CharField(max_length=20, default='NORMAL', help_text="LOW, NORMAL, HIGH, CRITICAL")
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


class CaseMessage(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=100, help_text="Name or role of sender")
    sender_type = models.CharField(max_length=20, default='customer', help_text="customer, agent, system")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'case_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.case.case_id} - {self.sender}: {self.text[:40]}"


class CaseEvidence(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='evidence_items')
    evidence_type = models.CharField(max_length=50, default='screenshot', help_text="screenshot, document, statement, other")
    url = models.URLField(blank=True, default='')
    filename = models.CharField(max_length=255, blank=True, default='')
    description = models.CharField(max_length=500, blank=True, default='')
    uploaded_by = models.CharField(max_length=100, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'case_evidence'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.case.case_id} - {self.evidence_type}: {self.filename or self.url}"


class CaseTimeline(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='timeline')
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    reason = models.CharField(max_length=500, blank=True, default='')
    triggered_by = models.CharField(max_length=100, default='system')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'case_timeline'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.case.case_id}: {self.from_status} → {self.to_status}"
