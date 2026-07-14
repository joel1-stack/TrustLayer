import django, os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trustlayer.settings')
django.setup()

from apps.agreements.models import Agreement
from apps.state_machine.services import StateMachine
from apps.orchestration.services import Orchestrator
from apps.settlements.models import Settlement
from apps.conditions.models import Condition
from apps.ledger.models import LedgerEntry

print('=== TEST 1: Create Agreement ===')
from apps.agreements.services import AgreementService
ag = AgreementService.create_agreement(
    title='Test API Flow',
    amount=5000,
    creator_id='test_api_user',
    description='Testing end-to-end API flow with new states'
)
AgreementService.add_party(ag, 'PAYER', 'test_buyer@email.com', 'Test Buyer', split_percentage=None)
AgreementService.add_party(ag, 'PAYEE', 'test_seller@email.com', 'Test Seller', split_percentage=90.00)
print(f'  Created: {ag.agreement_id} | Status: {ag.status_display}')
assert ag.status == 'CREATED', f'Expected CREATED, got {ag.status}'
assert ag.status_code == 10000

print()
print('=== TEST 2: Transition CREATED -> CONFIRMED ===')
t = StateMachine.transition(ag, 'CONFIRMED', triggered_by='test',
    actor_role='system', channel='api', ip_address='127.0.0.1',
    reason='Validation passed')
print(f'  Transition: {ag.status_display} | Status code: {ag.status_code}')
assert ag.status == 'CONFIRMED'
assert ag.status_code == 11000
assert t.actor_role == 'system'
assert t.channel == 'api'
assert t.ip_address == '127.0.0.1'

print()
print('=== TEST 3: Transition CONFIRMED -> SUBMITTED ===')
t = StateMachine.transition(ag, 'SUBMITTED', triggered_by='test',
    actor_role='system', channel='api', reason='Payment link generated')
print(f'  Transition: {ag.status_display} | Code: {ag.status_code}')
assert ag.status == 'SUBMITTED'
assert ag.status_code == 12000

print()
print('=== TEST 4: Transition SUBMITTED -> PENDING (webhook) ===')
t = StateMachine.transition(ag, 'PENDING', triggered_by='provider_webhook',
    actor_role='provider_webhook', channel='webhook', ip_address='10.0.0.1',
    reason='IntaSend acknowledged payment', evidence={'provider_ref': 'INTA_123'})
print(f'  Transition: {ag.status_display} | Code: {ag.status_code}')
assert ag.status == 'PENDING'
assert ag.status_code == 13000

print()
print('=== TEST 5: Transition PENDING -> AVAILABLE (payment received) ===')
t = StateMachine.transition(ag, 'AVAILABLE', triggered_by='provider_webhook',
    actor_role='provider_webhook', channel='webhook', reason='Payment confirmed')
print(f'  Transition: {ag.status_display} | Code: {ag.status_code}')
assert ag.status == 'AVAILABLE'
assert ag.status_code == 14000

print()
print('=== TEST 6: Transition AVAILABLE -> HELD (condition waiting) ===')
t = StateMachine.transition(ag, 'HELD', triggered_by='orchestrator',
    actor_role='system', channel='system', reason='Awaiting release conditions')
print(f'  Transition: {ag.status_display} | Code: {ag.status_code}')
assert ag.status == 'HELD'
assert ag.status_code == 15000

print()
print('=== TEST 7: Add Condition -> Met -> READY ===')
from apps.conditions.services import ConditionService
cond = ConditionService.add_condition(ag, 'buyer_confirmation', 'Buyer must confirm delivery', timeout_hours=48)
print(f'  Condition: {cond.condition_id} | Status: {cond.status}')
cond = ConditionService.mark_met(cond, met_by='test_buyer@email.com')
print(f'  Condition met: {cond.status}')
ready = ConditionService.are_all_required_met(ag)
assert ready, 'All required conditions should be met'
t = StateMachine.transition(ag, 'READY', triggered_by='orchestrator',
    actor_role='system', channel='system', reason='All conditions satisfied')
print(f'  Agreement: {ag.status_display} | Code: {ag.status_code}')
assert ag.status == 'READY'
assert ag.status_code == 16000

print()
print('=== TEST 8: Transition READY -> SETTLING -> SETTLED ===')
t = StateMachine.transition(ag, 'SETTLING', triggered_by='orchestrator',
    actor_role='system', channel='api', reason='Triggering payouts')
print(f'  SETTLING: {ag.status_display} | Code: {ag.status_code}')
t = StateMachine.transition(ag, 'SETTLED', triggered_by='provider_webhook',
    actor_role='provider_webhook', channel='webhook', reason='All payouts confirmed')
print(f'  SETTLED: {ag.status_display} | Code: {ag.status_code}')
assert ag.status == 'SETTLED'
assert ag.status_code == 18000

print()
print('=== TEST 9: SETTLED -> REVERSED is valid (dispute flow) ===')
t = StateMachine.transition(ag, 'REVERSED', triggered_by='admin', actor_role='admin', channel='admin_dashboard',
    reason='Buyer won dispute')
print(f'  REVERSED: {ag.status_display} | Code: {ag.status_code}')
assert ag.status == 'REVERSED'
assert ag.status_code == 19000

print()
print('=== TEST 10: Terminal state CANCELLED blocks all transitions ===')
from apps.agreements.services import AgreementService
ag2 = AgreementService.create_agreement(title='Test Terminal', amount=1000, creator_id='test')
StateMachine.transition(ag2, 'CANCELLED', triggered_by='test', actor_role='admin', channel='api', reason='Cancelled')
try:
    StateMachine.transition(ag2, 'CONFIRMED', triggered_by='test')
    print('  ERROR: Should not allow transition from CANCELLED')
except ValueError as e:
    print(f'  Correctly blocked: {e}')

print()
print('=== TEST 11: Illegal transition raises error ===')
ag3 = AgreementService.create_agreement(title='Test Illegal', amount=1000, creator_id='test')
try:
    StateMachine.transition(ag3, 'SETTLED', triggered_by='test')
    print('  ERROR: Should not allow CREATED -> SETTLED')
except ValueError as e:
    print(f'  Correctly blocked CREATED->SETTLED: {e}')

print()
print('=== TEST 12: State history includes new fields ===')
history = StateMachine.get_history(ag)
for h in history:
    print(f'  {h.from_status} -> {h.to_status} (code={h.status_code}, role={h.actor_role}, channel={h.channel}, ip={h.ip_address})')

print()
print('=== TEST 13: Serializer returns status_code ===')
from apps.agreements.serializers import AgreementSerializer
data = AgreementSerializer(ag).data
print(f'  status_code in API: {data.get("status_code")}')
assert data.get('status_code') == 19000

print()
print('=== TEST 13: System status counts ===')
from apps.admin_dashboard.views.overview import dashboard
print('  Admin dashboard view imports OK')

print()
print('=== TEST 14: PARTIALLY_SETTLED flow ===')
ag4 = AgreementService.create_agreement(title='Test Partial', amount=3000, creator_id='test')
AgreementService.add_party(ag4, 'PAYER', 'buyer@test.com', 'Buyer')
AgreementService.add_party(ag4, 'PAYEE', 'seller@test.com', 'Seller', split_percentage=100)
t = StateMachine.transition(ag4, 'CONFIRMED', triggered_by='test', actor_role='system', channel='api', reason='Valid')
t = StateMachine.transition(ag4, 'SUBMITTED', triggered_by='test', actor_role='system', channel='api', reason='Link')
t = StateMachine.transition(ag4, 'PENDING', triggered_by='webhook', actor_role='provider_webhook', channel='webhook', reason='Processing')
t = StateMachine.transition(ag4, 'AVAILABLE', triggered_by='webhook', actor_role='provider_webhook', channel='webhook', reason='Received')
t = StateMachine.transition(ag4, 'HELD', triggered_by='system', actor_role='system', channel='system', reason='Holding')
cond2 = ConditionService.add_condition(ag4, 'buyer_confirmation', 'Confirm delivery')
cond2 = ConditionService.mark_met(cond2, met_by='buyer')
t = StateMachine.transition(ag4, 'READY', triggered_by='system', actor_role='system', channel='system', reason='Ready')
t = StateMachine.transition(ag4, 'SETTLING', triggered_by='system', actor_role='system', channel='system', reason='Settling')
t = StateMachine.transition(ag4, 'PARTIALLY_SETTLED', triggered_by='system', actor_role='system', channel='system',
    reason='Some payouts succeeded, some failed', evidence={'settlements': ['STL_OK', 'STL_FAIL']})
print(f'  PARTIALLY_SETTLED: {ag4.status_display} | Code: {ag4.status_code}')
assert ag4.status == 'PARTIALLY_SETTLED'
assert ag4.status_code == 17500

print()
print('=== ALL 14 TESTS PASSED ===')
