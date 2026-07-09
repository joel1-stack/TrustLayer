from django.db import models

class StateTransition(models.Model):
    agreement = models.ForeignKey('agreements.Agreement', on_delete=models.CASCADE, related_name='transitions')
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    triggered_by = models.CharField(max_length=128, help_text='Who triggered this')
    reason = models.TextField(blank=True, default='')
    evidence = models.JSONField(default=dict, blank=True, help_text='Supporting data (receipt, doc ref, etc)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'state_transitions'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.agreement.agreement_id}: {self.from_status} \u2192 {self.to_status}"