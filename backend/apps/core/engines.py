"""
TrustLayer v1 — Engine models.
SLA, Audit, Notification, Evidence completeness.
"""
from django.db import models
from django.utils import timezone


class SLARule(models.Model):
    """Routing + SLA rules table. One row per case type."""
    case_type = models.CharField(max_length=50, unique=True)
    team = models.CharField(max_length=100)
    first_response_hours = models.IntegerField(default=24)
    resolution_hours = models.IntegerField(default=72)
    warning_at_percent = models.IntegerField(default=80, help_text='Warn agent at this % of deadline')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sla_rules'

    def __str__(self):
        return f"{self.case_type} → {self.team} ({self.resolution_hours}h)"


class AuditLog(models.Model):
    """Append-only audit log. Nobody edits, nobody deletes."""
    case_id = models.CharField(max_length=24, db_index=True)
    actor = models.CharField(max_length=128)
    actor_role = models.CharField(max_length=32, default='system')
    action = models.CharField(max_length=100)
    detail = models.TextField(blank=True, default='')
    from_status = models.CharField(max_length=30, blank=True, default='')
    to_status = models.CharField(max_length=30, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at}] {self.actor}: {self.action} on {self.case_id}"

    def save(self, *args, **kwargs):
        # Prevent updates — append-only
        if self.pk:
            raise ValueError("AuditLog entries cannot be modified")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog entries cannot be deleted")


class Notification(models.Model):
    """Notification log — one-way event feed."""
    EVENT_CHOICES = [
        ('case_created', 'Case Created'),
        ('evidence_uploaded', 'Evidence Uploaded'),
        ('info_requested', 'Info Requested'),
        ('resolved', 'Resolved'),
        ('verify_request', 'Verification Request'),
        ('reopened', 'Reopened'),
        ('closed', 'Closed'),
    ]
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('in_app', 'In-App'),
    ]

    case_id = models.CharField(max_length=24, db_index=True)
    event = models.CharField(max_length=50, choices=EVENT_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='in_app')
    recipient = models.CharField(max_length=255, help_text='Phone or email')
    subject = models.CharField(max_length=255, blank=True, default='')
    body = models.TextField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.event}] {self.case_id} → {self.recipient}"

    def mark_sent(self):
        self.sent = True
        self.sent_at = timezone.now()
        self.save(update_fields=['sent', 'sent_at'])
