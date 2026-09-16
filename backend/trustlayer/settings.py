"""
TrustLayer v1 — Django settings.
One loop: report → evidence → route → investigate → resolve → verify → closed.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

_hosts = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()] or ['*', 'localhost', '127.0.0.1', '0.0.0.0']

# ── v1 apps ──────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    # TrustLayer v1
    'apps.core',
    'apps.agreements',
    'apps.state_machine',
    'apps.api_v1',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'trustlayer.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

WSGI_APPLICATION = 'trustlayer.wsgi.application'

# ── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'trustlayer'),
        'USER': os.environ.get('DB_USER', 'trustlayer'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'TrustLayer2026!'),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': '5432',
    }
}

# ── Auth ─────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── i18n ─────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# ── Static & Media ───────────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Django REST Framework ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ── drf-spectacular (API docs) ──────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'TrustLayer API',
    'DESCRIPTION': (
        '## TrustLayer v1 — Case Lifecycle API\n\n'
        '**Base URL:** `https://miranda-stockish-spacially.ngrok-free.dev`\n\n'
        '---\n\n'
        '### What is TrustLayer?\n\n'
        'TrustLayer takes one customer problem, gathers the evidence around it, '
        'gets it to the right person, and produces a verified resolution.\n\n'
        'This is **not** a bank ledger, support ticket, or multi-org platform. '
        'It is a single verification loop that closes.\n\n'
        '---\n\n'
        '### Authentication\n\n'
        'All API endpoints use `AllowAny` — no API key required for v1.\n'
        'Agent actions (investigate, resolve) require session login via `/agent/login/`.\n\n'
        '---\n\n'
        '### The Lifecycle Loop\n\n'
        '```\n'
        '    ┌──────────────────────────────────────────────────┐\n'
        '    │              TRUSTLAYER CASE LOOP                 │\n'
        '    │                                                   │\n'
        '    │  1. CREATE ──→ OPEN                              │\n'
        '    │       │                                           │\n'
        '    │       ▼                                           │\n'
        '    │  2. EVIDENCE ──→ EVIDENCE_COLLECTION             │\n'
        '    │       │                                           │\n'
        '    │       ▼                                           │\n'
        '    │  3. INVESTIGATE ──→ INVESTIGATING                │\n'
        '    │       │                                           │\n'
        '    │       ▼                                           │\n'
        '    │  4. RESOLVE ──→ RESOLUTION_RECORDED              │\n'
        '    │       │                                           │\n'
        '    │       ▼                                           │\n'
        '    │  5. VERIFY ──→ VERIFYING                         │\n'
        '    │       │                                           │\n'
        '    │   ┌───┴───┐                                       │\n'
        '    │   ▼       ▼                                       │\n'
        '    │  YES      NO                                      │\n'
        '    │   │       │                                       │\n'
        '    │   ▼       ▼                                       │\n'
        '    │ RESOLVED  REOPENED ──→ back to INVESTIGATING     │\n'
        '    │   │                                               │\n'
        '    │   ▼                                               │\n'
        '    │ CLOSED (immutable record)                         │\n'
        '    └──────────────────────────────────────────────────┘\n'
        '```\n\n'
        '### Endpoints by Lifecycle Step\n\n'
        '| Step | Endpoint | Method | Description |\n'
        '|------|----------|--------|-------------|\n'
        '| 1. Report | `POST /api/v1/cases/create/` | Create case → OPEN |\n'
        '| 2. Evidence | `POST /api/v1/cases/{id}/evidence/` | Add evidence → EVIDENCE_COLLECTION |\n'
        '| 3. Investigate | `POST /api/v1/cases/{id}/investigate/` | Agent picks up → INVESTIGATING |\n'
        '| 4. Resolve | `POST /api/v1/cases/{id}/resolve/` | Record outcome → RESOLUTION_RECORDED |\n'
        '| 5. Verify | `POST /api/v1/cases/{id}/verify/` | Send to customer → VERIFYING |\n'
        '| 5b. Confirm | `POST /api/v1/cases/{id}/confirm/` | Customer confirms → RESOLVED or REOPENED |\n'
        '| 6. Close | `POST /api/v1/cases/{id}/close/` | Final close → CLOSED |\n\n'
        '### Other Endpoints\n\n'
        '| Endpoint | Method | Description |\n'
        '|----------|--------|-------------|\n'
        '| `GET /api/v1/cases/` | List all cases |\n'
        '| `GET /api/v1/cases/{id}/` | Full case detail with timeline, messages, evidence |\n'
        '| `POST /api/v1/cases/{id}/messages/` | Add message to case thread |\n'
        '| `GET /health/` | Health check → `{"status": "ok", "database": "ok"}` |\n\n'
        '---\n\n'
        '### Problem Types\n\n'
        '| Value | Label |\n'
        '|-------|-------|\n'
        '| `TRANSACTION_DISPUTE` | I don\'t recognize a transaction |\n'
        '| `PAYMENT_PROBLEM` | Payment problem |\n'
        '| `ACCOUNT_PROBLEM` | Account security issue |\n'
        '| `OTHER` | Other |\n\n'
        '### Resolution Types\n\n'
        '| Value | Label |\n'
        '|-------|-------|\n'
        '| `CONFIRMED_FRAUD` | Confirmed fraud |\n'
        '| `TRANSACTION_LEGITIMATE` | Transaction legitimate |\n'
        '| `CUSTOMER_ERROR` | Customer error |\n'
        '| `UNABLE_TO_DETERMINE` | Unable to determine |\n'
        '| `REFUNDED` | Refund initiated |\n\n'
        '---\n\n'
        '**Built in Kenya. Django + PostgreSQL + Redis.**'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'name': 'TrustLayer', 'url': 'https://github.com/joel1-stack/TrustLayer'},
    'LICENSE': {'name': 'MIT'},
}

# ── CORS / CSRF ──────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = [
    'https://miranda-stockish-spacially.ngrok-free.dev',
    'https://*.ngrok-free.dev',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# ── Sessions ─────────────────────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ── Security headers ─────────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False
