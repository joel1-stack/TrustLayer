"""
SMS adapter — Africa's Talking (primary) with generic HTTP fallback.
Set SMS_PROVIDER=africastalking in env to use AT.
Set SMS_PROVIDER=generic (default) for any REST SMS gateway.
"""
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def clean_phone(phone: str) -> str:
    phone = str(phone).strip().replace(' ', '').replace('-', '').lstrip('+')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif not phone.startswith('254'):
        phone = '254' + phone
    return phone


def send_sms(phone: str, message: str) -> dict:
    """
    Send SMS via configured provider.
    Returns {'success': True/False, 'error': str (if failed)}
    """
    phone    = clean_phone(phone)
    provider = getattr(settings, 'SMS_PROVIDER', 'generic')
    api_url  = getattr(settings, 'SMS_API_URL', '')
    api_key  = getattr(settings, 'SMS_API_KEY', '')
    sender   = getattr(settings, 'SMS_SENDER_ID', 'TrustLayer')

    if not api_url or not api_key:
        logger.warning(f'SMS not configured — skipped send to {phone}: {message[:60]}')
        return {'success': False, 'error': 'SMS not configured'}

    try:
        if provider == 'africastalking':
            # Africa's Talking API
            r = requests.post(
                api_url,  # https://api.africastalking.com/version1/messaging
                data={
                    'username': getattr(settings, 'SMS_USERNAME', 'sandbox'),
                    'to':       f'+{phone}',
                    'message':  message,
                    'from':     sender,
                },
                headers={
                    'apiKey':  api_key,
                    'Accept':  'application/json',
                },
                timeout=10,
            )
            r.raise_for_status()
            result = r.json()
            # AT returns SMSMessageData.Recipients[0].status == 'Success'
            recipients = result.get('SMSMessageData', {}).get('Recipients', [])
            success = any(rec.get('status') == 'Success' for rec in recipients)
            return {'success': success, 'raw': result}

        else:
            # Generic REST gateway (e.g. Twilio, Vonage, local gateway)
            r = requests.post(
                api_url,
                json={'to': phone, 'message': message, 'from': sender},
                headers={'apiKey': api_key, 'Content-Type': 'application/json'},
                timeout=10,
            )
            r.raise_for_status()
            return {'success': True}

    except Exception as e:
        logger.error(f'SMS send failed to {phone}: {e}')
        return {'success': False, 'error': str(e)}
