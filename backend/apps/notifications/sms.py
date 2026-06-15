"""
SMS adapter — Africa's Talking.
Sends SMS automatically when SMS_API_KEY is set in env.
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
    Send SMS via Africa's Talking API.
    Uses sandbox or production URL based on SMS_USERNAME.
    Returns {'success': True/False, 'error': str (if failed)}
    """
    phone    = clean_phone(phone)
    api_key  = getattr(settings, 'SMS_API_KEY', '')
    username = getattr(settings, 'SMS_USERNAME', 'sandbox')

    if not api_key:
        logger.warning(f'SMS not configured — skipped send to {phone}: {message[:60]}')
        return {'success': False, 'error': 'SMS_API_KEY not set'}

    # Auto-detect AT URL
    if username == 'sandbox':
        url = 'https://api.sandbox.africastalking.com/version1/messaging'
    else:
        url = 'https://api.africastalking.com/version1/messaging'

    payload = {
        'username': username,
        'to':       f'+{phone}',
        'message':  message,
    }

    # Only add 'from' for production (sandbox doesn't support custom sender)
    if username != 'sandbox':
        payload['from'] = getattr(settings, 'SMS_SENDER_ID', 'TrustLayer')

    headers = {
        'apiKey': api_key,
        'Accept': 'application/json',
    }

    try:
        r = requests.post(url, data=payload, headers=headers, timeout=10)
        result = r.json()
        recipients = result.get('SMSMessageData', {}).get('Recipients', [])
        success = any(rec.get('status') == 'Success' for rec in recipients)
        if success:
            logger.info(f"SMS sent to +{phone}: {message[:50]}...")
        else:
            logger.warning(f"SMS to +{phone} returned: {result}")
        return {'success': success, 'raw': result}
    except Exception as e:
        logger.error(f"SMS send failed to +{phone}: {e}")
        return {'success': False, 'error': str(e)}
