import django, os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trustlayer.settings')
django.setup()

from django.conf import settings
from apps.payments.adapters.registry import get_adapter

adapter = get_adapter('intasend')
print(f'INTASEND_BASE_URL = {settings.INTASEND_BASE_URL}')
print(f'INTASEND_SECRET_KEY = {"SET" if settings.INTASEND_SECRET_KEY else "EMPTY"}')
print(f'INTASEND_PUBLIC_KEY = {"SET" if settings.INTASEND_PUBLIC_KEY else "EMPTY"}')

try:
    import requests
    url = f'{settings.INTASEND_BASE_URL}/checkout/'
    print(f'\nAttempting POST to: {url}')
    payload = {'amount': '100', 'currency': 'KES', 'api_ref': 'test', 'phone_number': '', 'redirect_url': '', 'method': 'M-PESA'}
    headers = {'Authorization': f'Bearer {settings.INTASEND_SECRET_KEY}', 'Content-Type': 'application/json'}
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    print(f'Status: {resp.status_code}')
    print(f'Response: {resp.text[:500]}')
except requests.exceptions.ConnectionError as e:
    print(f'Connection Error (expected in sandbox): {e}')
except requests.exceptions.Timeout:
    print(f'Timeout (expected without internet)')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
