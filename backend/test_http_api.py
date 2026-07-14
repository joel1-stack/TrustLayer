import urllib.request, json

BASE = 'http://127.0.0.1:8000'

print('=== HTTP API TEST ===')
print()

# Test 1: GET /api/agreements/
try:
    req = urllib.request.Request(f'{BASE}/api/agreements/')
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    print(f'GET /api/agreements/ -> {resp.status}')
    print(f'  count={data["count"]}')
    if data['results']:
        r = data['results'][0]
        print(f'  keys: {list(r.keys())}')
        has_code = 'status_code' in r
        print(f'  has status_code: {has_code}')
        if has_code:
            print(f'  sample: id={r["agreement_id"]} status={r["status"]} code={r["status_code"]}')
except Exception as e:
    print(f'GET /api/agreements/ FAILED: {e}')

print()

# Test 2: POST /api/agreements/ (create new)
try:
    body = json.dumps({
        'title': 'HTTP E2E Test',
        'amount': 5000,
        'creator_id': 'http_test_user',
        'parties': [
            {'role': 'PAYER', 'name': 'Test Buyer', 'identifier': 'buyer@test.com'},
            {'role': 'PAYEE', 'name': 'Test Seller', 'identifier': 'seller@test.com', 'split_percentage': 90}
        ]
    }).encode()
    req = urllib.request.Request(f'{BASE}/api/agreements/', data=body,
        headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    agr_id = data.get('agreement_id')
    print(f'POST /api/agreements/ -> {resp.status}')
    print(f'  id={agr_id} status={data["status"]} code={data.get("status_code")}')
except Exception as e:
    print(f'POST /api/agreements/ FAILED: {e}')
    agr_id = None

print()

# Test 3: GET /api/agreements/<id>/
if agr_id:
    try:
        req = urllib.request.Request(f'{BASE}/api/agreements/{agr_id}/')
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        print(f'GET /api/agreements/{agr_id}/ -> {resp.status}')
        print(f'  status={data["status"]} code={data.get("status_code")}')
        print(f'  parties={len(data.get("parties", []))}')
    except Exception as e:
        print(f'GET /api/agreements/<id>/ FAILED: {e}')

print()

# Test 4: GET /api/ledger/agreement/<id>/
if agr_id:
    try:
        req = urllib.request.Request(f'{BASE}/api/ledger/agreement/{agr_id}/')
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        print(f'GET /api/ledger/agreement/{agr_id}/ -> {resp.status}')
        entries = data if isinstance(data, list) else []
        print(f'  entries: {len(entries)}')
    except Exception as e:
        print(f'GET /api/ledger/agreement/<id>/ FAILED: {e}')

print()

# Test 5: POST /api/payments/link/
if agr_id:
    try:
        body = json.dumps({'agreement_id': agr_id}).encode()
        req = urllib.request.Request(f'{BASE}/api/payments/link/', data=body,
            headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        print(f'POST /api/payments/link/ -> {resp.status}')
        print(f'  status={data["status"]} code={data.get("status_code")}')
        print(f'  payment_url={data.get("payment_url", "N/A")[:60]}')
    except Exception as e:
        print(f'POST /api/payments/link/ FAILED: {e}')

print()

# Test 6: GET /internal/health/
try:
    req = urllib.request.Request(f'{BASE}/internal/health/')
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    print(f'GET /internal/health/ -> {resp.status}')
    print(f'  keys: {list(data.keys())}')
    print(f'  status={data.get("status")}')
except Exception as e:
    print(f'GET /internal/health/ FAILED: {e}')

print()

# Test 7: GET /api/notifications/agreement/<id>/
if agr_id:
    try:
        req = urllib.request.Request(f'{BASE}/api/notifications/agreement/{agr_id}/')
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        entries = data if isinstance(data, list) else []
        print(f'GET /api/notifications/agreement/{agr_id}/ -> {resp.status}')
        print(f'  notifications: {len(entries)}')
    except Exception as e:
        print(f'GET /api/notifications/agreement/<id>/ FAILED: {e}')

print()
print('=== ALL HTTP TESTS COMPLETE ===')
