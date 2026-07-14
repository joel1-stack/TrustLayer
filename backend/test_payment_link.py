import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trustlayer.settings')
django.setup()

from apps.agreements.models import Agreement
from apps.agreements.services import AgreementService
from apps.payments.services import PaymentService

# Create a test agreement
ag = AgreementService.create_agreement(
    title='Payment Link Test',
    amount=100,
    creator_id='test_payment'
)
ag.refresh_from_db()
print(f'Agreement: {ag.agreement_id} status={ag.status}')

# Try generating payment link
try:
    tx, result = PaymentService.generate_payment_link(ag, phone='+254712345678', provider='intasend')
    print(f'Transaction: {tx.transaction_id}')
    print(f'Result: {result}')
    print(f'Success: {result.get("success")}')
    if result.get('success'):
        print(f'Payment URL: {result.get("payment_url")}')
    else:
        print(f'Error: {result.get("error")}')
except Exception as e:
    print(f'Exception: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
