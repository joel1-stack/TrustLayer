import urllib.request, urllib.parse, http.cookiejar, json, re

BASE = 'http://127.0.0.1:8000'
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# Step 1: GET login page to get CSRF token
print('=== Step 1: GET /admin/login/ ===')
req = urllib.request.Request(f'{BASE}/admin/login/')
resp = opener.open(req)
html = resp.read().decode()
match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', html)
csrf = match.group(1) if match else 'NO_CSRF'
print(f'  CSRF token: {csrf[:20]}...')
print(f'  Status: {resp.status}')

# Step 2: POST login with credentials
print()
print('=== Step 2: POST /admin/login/ (joelkaunda15 / wherby) ===')
data = urllib.parse.urlencode({
    'username': 'joelkaunda15',
    'password': 'wherby',
    'csrfmiddlewaretoken': csrf,
}).encode()
req = urllib.request.Request(f'{BASE}/admin/login/', data=data,
    headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': f'{BASE}/admin/login/'})
# Don't follow redirects so we can see the status
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
no_redirect_opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(jar))
try:
    resp = no_redirect_opener.open(req)
    print(f'  Status: {resp.status}')
    print(f'  Location: {resp.headers.get("Location", "N/A")}')
except urllib.error.HTTPError as e:
    print(f'  Status: {e.code}')
    print(f'  Location: {e.headers.get("Location", "N/A")}')

# Step 3: Follow redirect to dashboard
print()
print('=== Step 3: Follow redirect to dashboard ===')
req = urllib.request.Request(f'{BASE}/admin/dashboard/')
resp = opener.open(req)
html = resp.read().decode()
print(f'  Status: {resp.status}')
print(f'  Title present: {"TrustLayer" in html}')
print(f'  Logged in as present: {"Joel" in html or "dashboard" in html.lower()}')
print(f'  Page length: {len(html)} chars')

# Step 4: Test customer portal login page
print()
print('=== Step 4: GET /portal/login/ ===')
req = urllib.request.Request(f'{BASE}/portal/login/')
resp = urllib.request.urlopen(req)
html = resp.read().decode()
print(f'  Status: {resp.status}')
print(f'  Portal login form: {"password" in html.lower()}')
print(f'  Page length: {len(html)} chars')

print()
print('=== LOGIN TESTS COMPLETE ===')
