from decimal import Decimal
from django.test import TestCase
from .models import Agreement, AgreementParty
from .services import AgreementService

class AgreementServiceTests(TestCase):

    def setUp(self):
        self.agreement = AgreementService.create_agreement(
            title='Test Deal',
            amount=Decimal('1000.00'),
            creator_id='org_123',
        )

    def test_create_agreement(self):
        self.assertEqual(self.agreement.title, 'Test Deal')
        self.assertEqual(self.agreement.amount, Decimal('1000.00'))
        self.assertEqual(self.agreement.status, Agreement.Status.CREATED)
        self.assertTrue(self.agreement.agreement_id.startswith('AGR'))

    def test_add_parties_and_calculate_splits(self):
        payer = AgreementService.add_party(
            self.agreement, AgreementParty.Role.PAYER, 'payer@test.com', 'Payer One',
            split_percentage=Decimal('60.00'),
        )
        payee = AgreementService.add_party(
            self.agreement, AgreementParty.Role.PAYEE, 'payee@test.com', 'Payee One',
            split_fixed=Decimal('400.00'),
        )
        splits = AgreementService.calculate_splits(self.agreement)
        self.assertEqual(len(splits), 2)
        payer_split = next(s for s in splits if s['party'].role == 'PAYER')
        payee_split = next(s for s in splits if s['party'].role == 'PAYEE')
        self.assertEqual(payer_split['amount'], Decimal('600.00'))
        self.assertEqual(payee_split['amount'], Decimal('400.00'))