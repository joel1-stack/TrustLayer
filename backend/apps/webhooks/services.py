import json
import hmac
import hashlib
import secrets
import requests
from django.db import models
from django.utils import timezone
from datetime import timedelta
from .models import WebhookEndpoint, WebhookDelivery


class WebhookService:
    MAX_RETRIES  = 5
    RETRY_DELAYS = [5, 15, 60, 300, 900]

    @classmethod
    def create_endpoint(cls, merchant, url, events, description=''):
        secret   = secrets.token_hex(32)
        endpoint = WebhookEndpoint.objects.create(
            merchant=merchant,
            url=url,
            events=events if isinstance(events, list) else [events],
            secret=secret,
            description=description,
        )
        return {'endpoint_id': str(endpoint.id), 'url': url, 'secret': secret, 'events': events}

    @classmethod
    def trigger(cls, merchant, event_type, payload):
        endpoints = WebhookEndpoint.objects.filter(
            merchant=merchant, is_active=True
        ).filter(
            models.Q(events__contains=[event_type]) | models.Q(events__contains=['all'])
        )
        return [cls._send(ep, event_type, payload) for ep in endpoints]

    @classmethod
    def _send(cls, endpoint, event_type, payload):
        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint, event_type=event_type, payload=payload, attempt_count=0
        )
        sig     = cls._sign(payload, endpoint.secret)
        headers = {
            'Content-Type':           'application/json',
            'X-TrustLayer-Signature': sig,
            'X-TrustLayer-Event':     event_type,
            'X-TrustLayer-Delivery':  str(delivery.id),
            'User-Agent':             'TrustLayer-Webhook/1.0',
        }
        delivery.headers = headers
        delivery.save()
        return cls._attempt(delivery)

    @classmethod
    def _attempt(cls, delivery):
        delivery.attempt_count += 1
        try:
            r = requests.post(delivery.endpoint.url, json=delivery.payload, headers=delivery.headers, timeout=30)
            delivery.http_status   = r.status_code
            delivery.response_body = r.text[:1000]
            if r.status_code == 200:
                delivery.status       = 'SUCCESS'
                delivery.completed_at = timezone.now()
                delivery.endpoint.last_triggered = timezone.now()
                delivery.endpoint.save()
            else:
                delivery.status        = 'FAILED'
                delivery.error_message = f"HTTP {r.status_code}"
                cls._schedule_retry(delivery)
        except Exception as e:
            delivery.status        = 'FAILED'
            delivery.error_message = str(e)
            cls._schedule_retry(delivery)
        delivery.save()
        return delivery

    @classmethod
    def _schedule_retry(cls, delivery):
        if delivery.attempt_count < cls.MAX_RETRIES:
            delay = cls.RETRY_DELAYS[min(delivery.attempt_count - 1, len(cls.RETRY_DELAYS) - 1)]
            delivery.next_retry = timezone.now() + timedelta(seconds=delay)
            delivery.status     = 'RETRYING'

    @classmethod
    def _sign(cls, payload, secret):
        body = json.dumps(payload, sort_keys=True)
        return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    @classmethod
    def verify_signature(cls, payload, signature, secret):
        return hmac.compare_digest(cls._sign(payload, secret), signature)

    @classmethod
    def process_retries(cls):
        for d in WebhookDelivery.objects.filter(status='RETRYING', next_retry__lte=timezone.now()):
            cls._attempt(d)
