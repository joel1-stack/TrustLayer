import uuid
from django.db import models


class WebhookEndpoint(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant    = models.ForeignKey('merchants.Merchant', on_delete=models.CASCADE, related_name='webhooks')
    url         = models.URLField()
    events      = models.JSONField(default=list)
    secret      = models.CharField(max_length=100)
    is_active   = models.BooleanField(default=True)
    description = models.CharField(max_length=200, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webhook_endpoints'

    def __str__(self):
        return f"{self.merchant.company_name} — {self.url}"


class WebhookDelivery(models.Model):
    STATUS_CHOICES = [('PENDING','Pending'),('SUCCESS','Success'),('FAILED','Failed'),('RETRYING','Retrying')]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint      = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type    = models.CharField(max_length=50)
    payload       = models.JSONField()
    headers       = models.JSONField(default=dict)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    http_status   = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    attempt_count = models.IntegerField(default=0)
    next_retry    = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    completed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webhook_deliveries'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} — {self.status}"
