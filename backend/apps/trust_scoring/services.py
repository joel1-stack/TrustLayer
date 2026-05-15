from django.utils import timezone
from .models import TrustScore, TrustScoreLog


class TrustScoringService:
    WEIGHTS = {'payment_reliability': 0.30, 'dispute_rate': 0.25, 'account_age': 0.15, 'volume': 0.15, 'verification': 0.15}

    @classmethod
    def get_or_create(cls, merchant):
        score, _ = TrustScore.objects.get_or_create(merchant=merchant, defaults={'overall_score': 50})
        return score

    @classmethod
    def calculate(cls, merchant):
        from apps.escrow.models import EscrowDeal
        score = cls.get_or_create(merchant)
        deals = EscrowDeal.objects.filter(merchant=merchant)
        total = deals.count()
        if total > 0:
            successful = deals.filter(status__in=['RELEASED', 'HELD']).count()
            disputed   = deals.filter(status='DISPUTED').count()
            score.payment_reliability   = int((successful / total) * 100)
            score.dispute_rate_score    = max(0, int(100 - (disputed / total * 100)))
            score.total_transactions    = total
            score.successful_transactions = successful
            score.disputed_transactions = disputed
        age = (timezone.now() - merchant.created_at).days
        score.account_age_score = 20 if age < 7 else 40 if age < 30 else 60 if age < 90 else 80 if age < 365 else 100
        vol = sum(d.amount for d in deals)
        score.volume_score = 20 if vol < 10000 else 40 if vol < 50000 else 60 if vol < 100000 else 80 if vol < 500000 else 100
        score.verification_score = 100 if getattr(merchant, 'is_verified', False) else 50
        score.overall_score = int(
            score.payment_reliability * cls.WEIGHTS['payment_reliability'] +
            score.dispute_rate_score  * cls.WEIGHTS['dispute_rate'] +
            score.account_age_score   * cls.WEIGHTS['account_age'] +
            score.volume_score        * cls.WEIGHTS['volume'] +
            score.verification_score  * cls.WEIGHTS['verification']
        )
        score.score_history = (score.score_history + [{'date': timezone.now().isoformat(), 'score': score.overall_score}])[-30:]
        score.save()
        return score

    @classmethod
    def update(cls, merchant, reason):
        old = cls.get_or_create(merchant).overall_score
        new = cls.calculate(merchant)
        TrustScoreLog.objects.create(merchant=merchant, old_score=old, new_score=new.overall_score, reason=reason)
        return new

    @classmethod
    def details(cls, merchant):
        s = cls.get_or_create(merchant)
        r = 'A+' if s.overall_score >= 90 else 'A' if s.overall_score >= 80 else 'B' if s.overall_score >= 70 else 'C' if s.overall_score >= 60 else 'D' if s.overall_score >= 50 else 'F'
        return {'overall': s.overall_score, 'rating': r, 'metrics': {'total': s.total_transactions, 'successful': s.successful_transactions, 'disputed': s.disputed_transactions}}
