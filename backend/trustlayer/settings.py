"""
Django settings for TrustLayer project.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Render sets ALLOWED_HOSTS via env; fallback allows local + Docker
_hosts = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()] or ['*', 'localhost', '127.0.0.1', '0.0.0.0']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    # TrustLayer Core Engines
    'apps.agreements',
    'apps.state_machine',
    'apps.conditions',
    'apps.ledger',
    'apps.settlements',
    'apps.notifications',
    'apps.orchestration',
    'apps.payments',
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

# Database — supports DATABASE_URL (Render) or individual env vars (Docker)
import dj_database_url
_db_url = os.environ.get('DATABASE_URL', '')
if _db_url:
    DATABASES = {'default': dj_database_url.config(default=_db_url, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'trustlayer_db'),
            'USER': os.environ.get('DB_USER', 'joel'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'SecurePass123!'),
            'HOST': os.environ.get('DB_HOST', 'db'),
            'PORT': '5432',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

CORS_ALLOW_ALL_ORIGINS = True

_redis_url = f"redis://{os.environ.get('REDIS_HOST', 'redis_cache')}:{os.environ.get('REDIS_PORT', '6379')}"

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', f'{_redis_url}/1'),
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}

CELERY_BROKER_URL     = os.environ.get('CELERY_BROKER_URL') or os.environ.get('REDIS_URL', f'{_redis_url}/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or os.environ.get('REDIS_URL', f'{_redis_url}/0')

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'check-condition-timeouts': {
        'task':     'apps.conditions.services.check_condition_timeouts',
        'schedule': crontab(minute='*/5'),
    },
}

# M-Pesa / Daraja
MPESA_ENVIRONMENT    = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')
MPESA_CONSUMER_KEY   = os.environ.get('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
MPESA_SHORTCODE       = os.environ.get('MPESA_SHORTCODE', '174379')
MPESA_PASSKEY         = os.environ.get('MPESA_PASSKEY', '')
MPESA_CALLBACK_URL    = os.environ.get('MPESA_CALLBACK_URL', '')
MPESA_API_KEY         = os.environ.get('MPESA_API_KEY', 'devkey')

# M-Pesa B2C (Business-to-Customer — payout to sellers)
MPESA_INITIATOR_NAME     = os.environ.get('MPESA_INITIATOR_NAME', 'testinitiator')
MPESA_INITIATOR_PASSWORD = os.environ.get('MPESA_INITIATOR_PASSWORD', '')
MPESA_B2C_RESULT_URL     = os.environ.get('MPESA_B2C_RESULT_URL', '')
MPESA_B2C_TIMEOUT_URL    = os.environ.get('MPESA_B2C_TIMEOUT_URL', '')

# IntaSend (Collect + Payout — live wallet)
INTASEND_PUBLIC_KEY   = os.environ.get('INTASEND_PUBLIC_KEY', '')
INTASEND_SECRET_KEY   = os.environ.get('INTASEND_SECRET_KEY', '')
INTASEND_BASE_URL     = os.environ.get('INTASEND_BASE_URL', 'https://payment.intasend.com/api/v1')
INTASEND_CALLBACK_URL = os.environ.get('INTASEND_CALLBACK_URL', '')

# SMS Notifications
SMS_PROVIDER  = os.environ.get('SMS_PROVIDER', 'generic')   # 'africastalking' or 'generic'
SMS_API_URL   = os.environ.get('SMS_API_URL', '')
SMS_API_KEY   = os.environ.get('SMS_API_KEY', '')
SMS_SENDER_ID = os.environ.get('SMS_SENDER_ID', 'TrustLayer')
SMS_USERNAME  = os.environ.get('SMS_USERNAME', 'sandbox')    # Africa's Talking username

# Admin
TRUSTLAYER_ADMIN_TOKEN = os.environ.get('TRUSTLAYER_ADMIN_TOKEN', 'change-me-in-production')
