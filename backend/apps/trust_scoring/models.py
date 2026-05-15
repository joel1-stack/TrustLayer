from django.db import models


class TrustScore(models.Model):
    merchant              = models.OneToOneField('merchants.Merchant', on_delete=models.CASCADE, related_name='trust_score_obj')
    payment_reliability   = models.IntegerField(default=50)
    dispute_rate_score    = models.IntegerField(default=50)
    account_age_score     = models.IntegerField(default=50)
    volume_score          = models.IntegerField(default=50)
    verification_score    = models.IntegerField(default=50)
    overall_score         = models.IntegerField(default=50)
    total_transactions    = models.IntegerField(default=0)
    successful_transactions = models.IntegerField(default=0)
    disputed_transactions = models.IntegerField(default=0)
    refunded_transactions = models.IntegerField(default=0)
    score_history         = models.JSONField(default=list)
    updated_at            = models.DateTimeField(auto_now=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trust_scores'

    def __str__(self):
        return f"{self.merchant.company_name}: {self.overall_score}"


class TrustScoreLog(models.Model):
    merchant   = models.ForeignKey('merchants.Merchant', on_delete=models.CASCADE)
    old_score  = models.IntegerField()
    new_score  = models.IntegerField()
    reason     = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trust_score_logs'
