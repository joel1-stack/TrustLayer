from django.db import models


class DiagnosisRecord(models.Model):
    class DiagnosedBy(models.TextChoices):
        SYSTEM = 'system', 'System'
        AGENT = 'agent', 'Agent'

    case = models.ForeignKey('agreements.Case', on_delete=models.CASCADE, related_name='diagnosis_records')
    root_cause = models.CharField(max_length=512)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    evidence = models.JSONField(default=list)
    recommended_actions = models.JSONField(default=list)
    diagnosed_by = models.CharField(max_length=16, choices=DiagnosedBy.choices, default=DiagnosedBy.SYSTEM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'diagnosis_records'
        ordering = ['-created_at']

    def __str__(self):
        return f"Diagnosis({self.case_id}) - {self.root_cause} [{self.confidence}]"
