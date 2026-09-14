from django.db import models


class PolicyRule(models.Model):
    class RequiredClearance(models.TextChoices):
        L1 = 'L1', 'Level 1'
        L2 = 'L2', 'Level 2'
        L3 = 'L3', 'Level 3'

    class RiskLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    rule_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    action_type = models.CharField(max_length=128)
    conditions = models.JSONField(default=dict)
    required_clearance = models.CharField(max_length=8, choices=RequiredClearance.choices, default=RequiredClearance.L1)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.choices, default=RiskLevel.LOW)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'policy_rules'
        ordering = ['-created_at']

    def __str__(self):
        return f"PolicyRule({self.rule_id}) - {self.name}"


class PolicyDecision(models.Model):
    class Decision(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        DENIED = 'denied', 'Denied'
        ESCALATED = 'escalated', 'Escalated'

    case = models.ForeignKey('agreements.Case', on_delete=models.CASCADE, related_name='policy_decisions')
    rule = models.ForeignKey(PolicyRule, on_delete=models.CASCADE, related_name='decisions')
    decision = models.CharField(max_length=16, choices=Decision.choices, default=Decision.APPROVED)
    reason = models.TextField(blank=True)
    decided_by = models.CharField(max_length=128)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'policy_decisions'
        ordering = ['-decided_at']

    def __str__(self):
        return f"PolicyDecision({self.case_id}) - {self.rule.rule_id} [{self.decision}]"
