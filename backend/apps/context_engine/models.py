from django.db import models


class ContextRecord(models.Model):
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        PARTIAL = 'partial', 'Partial'
        FAILED = 'failed', 'Failed'

    case = models.ForeignKey('agreements.Case', on_delete=models.CASCADE, related_name='context_records')
    source_adapter = models.CharField(max_length=128)
    query_type = models.CharField(max_length=128)
    raw_response = models.JSONField(default=dict)
    assembled_context = models.JSONField(default=dict)
    latency_ms = models.IntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUCCESS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'context_records'
        ordering = ['-created_at']

    def __str__(self):
        return f"ContextRecord({self.case_id}) - {self.source_adapter} [{self.status}]"
