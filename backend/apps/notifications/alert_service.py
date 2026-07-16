import json
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from apps.admin_dashboard.models import SecurityAlert, LoginAttempt

logger = logging.getLogger(__name__)

ALERT_EMAIL = 'joelkaunda15@gmail.com'
ALERT_PHONE = '+254715641339'

BRUTE_FORCE_THRESHOLD = 10
SUSPICIOUS_IP_THRESHOLD = 20


def send_security_notification(alert):
    subject = f'[SECURITY] TrustLayer - {alert.severity.upper()}: {alert.alert_type}'
    message = (
        f'Security Alert: {alert.alert_type}\n'
        f'Severity: {alert.severity}\n'
        f'Message: {alert.message}\n'
        f'IP: {alert.ip_address or "N/A"}\n'
        f'Time: {alert.created_at}\n'
        f'Details: {json.dumps(alert.detail, indent=2)}\n\n'
        f'Action required. Log into TrustLayer Admin to review.'
    )

    try:
        send_mail(
            subject, message, settings.DEFAULT_FROM_EMAIL,
            [ALERT_EMAIL], fail_silently=True
        )
        alert.notified_via_email = True
        logger.info(f'Security alert email sent to {ALERT_EMAIL}')
    except Exception as e:
        logger.error(f'Failed to send security alert email: {e}')

    try:
        sms_provider = getattr(settings, 'SMS_PROVIDER', 'generic')
        if sms_provider == 'africastalking' and settings.SMS_API_KEY:
            import requests
            resp = requests.post(
                settings.SMS_API_URL or 'https://api.africastalking.com/version1/messaging',
                data={
                    'username': settings.SMS_USERNAME or 'sandbox',
                    'to': ALERT_PHONE,
                    'message': f'[TrustLayer SECURITY] {alert.severity}: {alert.alert_type} - {alert.message[:120]}',
                    'from': settings.SMS_SENDER_ID or 'TrustLayer',
                },
                headers={'ApiKey': settings.SMS_API_KEY, 'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10,
            )
            if resp.status_code == 201 or resp.status_code == 200:
                alert.notified_via_sms = True
                logger.info(f'Security SMS sent to {ALERT_PHONE}')
        else:
            logger.info(f'SMS provider {sms_provider} not configured for alerts')
    except Exception as e:
        logger.error(f'Failed to send security SMS: {e}')

    alert.save(update_fields=['notified_via_email', 'notified_via_sms'])


def check_and_alert_brute_force(ip_address, username=''):
    recent = LoginAttempt.objects.filter(
        ip_address=ip_address,
        success=False,
        timestamp__gte=timezone.now() - timedelta(hours=1)
    ).count()

    if recent >= BRUTE_FORCE_THRESHOLD:
        existing = SecurityAlert.objects.filter(
            alert_type='brute_force',
            ip_address=ip_address,
            resolved=False,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).exists()
        if not existing:
            alert = SecurityAlert.objects.create(
                alert_type='brute_force',
                severity='high',
                message=f'Brute force attack detected from {ip_address} ({recent} failed attempts in 1 hour)',
                detail={'failed_attempts': recent, 'recent_username': username},
                ip_address=ip_address,
            )
            send_security_notification(alert)
            return alert

    suspicious_ips = LoginAttempt.objects.values('ip_address').annotate(
        cnt=models.Count('id')
    ).filter(cnt__gte=SUSPICIOUS_IP_THRESHOLD)

    for entry in suspicious_ips:
        sip = entry['ip_address']
        if sip and sip != ip_address:
            existing = SecurityAlert.objects.filter(
                alert_type='suspicious_activity',
                ip_address=sip,
                resolved=False,
                created_at__gte=timezone.now() - timedelta(hours=6)
            ).exists()
            if not existing:
                alert = SecurityAlert.objects.create(
                    alert_type='suspicious_activity',
                    severity='medium',
                    message=f'Suspicious activity from {sip} ({entry["cnt"]} total attempts)',
                    detail={'total_attempts': entry['cnt']},
                    ip_address=sip,
                )
                send_security_notification(alert)
                return alert

    return None


def check_and_alert_unauthorized_access(ip_address, path):
    existing = SecurityAlert.objects.filter(
        alert_type='unauthorized_access',
        ip_address=ip_address,
        resolved=False,
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).exists()
    if not existing:
        alert = SecurityAlert.objects.create(
            alert_type='unauthorized_access',
            severity='medium',
            message=f'Unauthorized access attempt from {ip_address} to {path}',
            detail={'path': path},
            ip_address=ip_address,
        )
        send_security_notification(alert)
        return alert
    return None


try:
    from django.db import models
except ImportError:
    models = None
