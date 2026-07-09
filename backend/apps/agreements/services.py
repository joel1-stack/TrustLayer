from decimal import Decimal
from .models import Agreement, AgreementParty

class AgreementService:

    @staticmethod
    def create_agreement(title, amount, creator_id, description='', currency='KES', creator_type='organization', metadata=None):
        agreement = Agreement.objects.create(
            title=title,
            amount=amount,
            currency=currency,
            creator_id=creator_id,
            creator_type=creator_type,
            description=description,
            metadata=metadata or {},
        )
        return agreement

    @staticmethod
    def add_party(agreement, role, identifier, name, split_percentage=None, split_fixed=None, payout_method='', payout_details=None):
        party = AgreementParty.objects.create(
            agreement=agreement,
            role=role,
            identifier=identifier,
            name=name,
            payout_method=payout_method,
            split_percentage=split_percentage,
            split_fixed=split_fixed,
            payout_details=payout_details or {},
        )
        return party

    @staticmethod
    def calculate_splits(agreement):
        parties = agreement.parties.all()
        total_pct = sum(p.split_percentage or 0 for p in parties)
        total_fixed = sum(p.split_fixed or 0 for p in parties)

        splits = []
        assigned_amount = Decimal('0.00')
        remainder_recipient = None

        for p in parties:
            amount = Decimal('0.00')
            if p.split_percentage:
                amount += (agreement.amount * p.split_percentage / Decimal('100.00')).quantize(Decimal('0.01'))
            if p.split_fixed:
                amount += p.split_fixed
            if p.split_percentage or p.split_fixed:
                assigned_amount += amount
                splits.append({'party': p, 'amount': amount})
            else:
                remainder_recipient = p

        # Assign remainder to the party without a split (default: PAYEE)
        if remainder_recipient:
            remainder = agreement.amount - assigned_amount
            if remainder > 0:
                splits.append({'party': remainder_recipient, 'amount': remainder})

        return splits

    @staticmethod
    def get_agreement(agreement_id):
        return Agreement.objects.filter(agreement_id=agreement_id).first()