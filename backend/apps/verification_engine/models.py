from django.db import models


class VerificationCheck(models.Model):
    case = models.ForeignKey('agreements.Case', on_delete=models.CASCADE, related_name='verification_checks')
    check_type = models.CharField(max_length=128)
    expected_value = models.JSONField(default=dict)
    actual_value = models.JSONField(default=dict)
    passed = models.BooleanField(default=False)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'verification_checks'
        ordering = ['-checked_at']

    def __str__(self):
        return f"VerificationCheck({self.case_id}) - {self.check_type} [{'PASS' if self.passed else 'FAIL'}]"


class VerificationResult(models.Model):
    case = models.ForeignKey('agreements.Case', on_delete=models.CASCADE, related_name='verification_results')
    overall_passed = models.BooleanField(default=False)
    checks_total = models.IntegerField(default=0)
    checks_passed = models.IntegerField(default=0)
    recovery_confirmed = models.BooleanField(default=False)
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'verification_results'
        ordering = ['-verified_at']

    def __str__(self):
        return f"VerificationResult({self.case_id}) - {'PASS' if self.overall_passed else 'FAIL'} ({self.checks_passed}/{self.checks_total})"
