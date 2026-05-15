import uuid
from django.db import models


class Notification(models.Model):
    CHANNEL_CHOICES = [('SMS','SMS'),('EMAIL','Email'),('WEBHOOK','Webhook')]
    STATUS_CHOICES  = [('PENDING','Pending'),('SENT','Sent'),('FAILED','Failed'),('DELIVERED','Delivered')]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient     = models.CharField(max_length=100)
    channel       = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    template_name = models.CharField(max_length=100)
    subject       = models.CharField(max_length=200, blank=True)
    body          = models.TextField()
    data          = models.JSONField(default=dict)
    external_id   = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    sent_at       = models.DateTimeField(null=True, blank=True)
    delivered_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.channel} to {self.recipient} — {self.status}"
