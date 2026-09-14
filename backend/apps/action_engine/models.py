from django.db import models


class ActionPlan(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        APPROVED = 'approved', 'Approved'
        EXECUTING = 'executing', 'Executing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    case = models.ForeignKey('agreements.Case', on_delete=models.CASCADE, related_name='action_plans')
    action_type = models.CharField(max_length=128)
    parameters = models.JSONField(default=dict)
    priority = models.IntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    approved_by = models.CharField(max_length=128, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'action_plans'
        ordering = ['-created_at']

    def __str__(self):
        return f"ActionPlan({self.case_id}) - {self.action_type} [{self.status}]"


class ActionResult(models.Model):
    class Outcome(models.TextChoices):
        SUCCESS = 'success', 'Success'
        PARTIAL = 'partial', 'Partial'
        FAILED = 'failed', 'Failed'

    plan = models.ForeignKey(ActionPlan, on_delete=models.CASCADE, related_name='results')
    outcome = models.CharField(max_length=16, choices=Outcome.choices, default=Outcome.SUCCESS)
    response_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    duration_ms = models.IntegerField(default=0)

    class Meta:
        db_table = 'action_results'
        ordering = ['-executed_at']

    def __str__(self):
        return f"ActionResult({self.plan_id}) - {self.outcome}"
