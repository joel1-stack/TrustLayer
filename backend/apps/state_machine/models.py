from django.db import models

class StateTransition(models.Model):
    agreement = models.ForeignKey('agreements.Agreement', on_delete=models.CASCADE, related_name='transitions')
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    status_code = models.IntegerField(null=True, blank=True, help_text='Numeric code for the target state')
    triggered_by = models.CharField(max_length=128, help_text='Who triggered this')
    actor_role = models.CharField(max_length=32, blank=True, default='', help_text='Role of the actor: system, admin, customer, provider_webhook')
    channel = models.CharField(max_length=32, blank=True, default='', help_text='Channel: api, webhook, admin_dashboard, portal, system')
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text='IP address of the requester')
    reason = models.TextField(blank=True, default='')
    evidence = models.JSONField(default=dict, blank=True, help_text='Supporting data (receipt, doc ref, etc)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'state_transitions'
        ordering = ['created_at']

    def __str__(self):
        code_str = f" ({self.status_code})" if self.status_code else ""
        return f"{self.agreement.agreement_id}: {self.from_status} -> {self.to_status}{code_str}"
