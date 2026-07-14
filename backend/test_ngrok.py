import urllib.request, json

BASE = 'https://miranda-stockish-spacially.ngrok-free.dev'

print('=== NGROK ENDPOINT TEST ===')
print()

# Test 1: Health
try:
    req = urllib.request.Request(f'{BASE}/internal/health/')
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    print(f'GET /internal/health/ -> {resp.status}')
    print(f'  database: {data.get("database", {}).get("status")}')
    print(f'  engines: {len(data.get("engines", {}))}')
except Exception as e:
    print(f'Health check FAILED: {e}')

print()

# Test 2: Agreements list
try:
    req = urllib.request.Request(f'{BASE}/api/agreements/')
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    print(f'GET /api/agreements/ -> {resp.status}')
    print(f'  count: {data["count"]}')
    if data['results']:
        r = data['results'][0]
        print(f'  sample: id={r["agreement_id"]} status={r["status"]} code={r.get("status_code")}')
except Exception as e:
    print(f'Agreements list FAILED: {e}')

print()

# Test 3: Create agreement via ngrok
try:
    body = json.dumps({
        'title': 'Ngrok E2E Test',
        'amount': 1000,
        'creator_id': 'ngrok_test',
        'parties': [
            {'role': 'PAYER', 'name': 'Ngrok Buyer', 'identifier': 'buyer@ngrok.com'},
            {'role': 'PAYEE', 'name': 'Ngrok Seller', 'identifier': 'seller@ngrok.com', 'split_percentage': 95}
        ]
    }).encode()
    req = urllib.request.Request(f'{BASE}/api/agreements/', data=body,
        headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    print(f'POST /api/agreements/ -> {resp.status}')
    print(f'  id={data["agreement_id"]} status={data["status"]} code={data.get("status_code")}')
    agr_id = data['agreement_id']
except Exception as e:
    print(f'Create agreement FAILED: {e}')
    agr_id = None

print()

# Test 4: Payment link via ngrok
if agr_id:
    try:
        body = json.dumps({'agreement_id': agr_id}).encode()
        req = urllib.request.Request(f'{BASE}/api/payments/link/', data=body,
            headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        print(f'POST /api/payments/link/ -> {resp.status}')
        print(f'  status={data["status"]} code={data.get("status_code")}')
    except Exception as e:
        print(f'Payment link FAILED: {e}')

print()

# Test 5: Admin login page via ngrok
try:
    req = urllib.request.Request(f'{BASE}/admin/login/')
    resp = urllib.request.urlopen(req, timeout=10)
    html = resp.read().decode()
    has_form = 'csrfmiddlewaretoken' in html
    print(f'GET /admin/login/ -> {resp.status}')
    print(f'  Login form present: {has_form}')
except Exception as e:
    print(f'Admin login FAILED: {e}')

print()

# Test 6: Portal login via ngrok
try:
    req = urllib.request.Request(f'{BASE}/portal/login/')
    resp = urllib.request.urlopen(req, timeout=10)
    html = resp.read().decode()
    has_form = 'password' in html.lower()
    print(f'GET /portal/login/ -> {resp.status}')
    print(f'  Portal form present: {has_form}')
except Exception as e:
    print(f'Portal login FAILED: {e}')

print()
print('=== NGROK TESTS COMPLETE ===')
