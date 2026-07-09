from django.urls import path
from . import webhooks

urlpatterns = [
    path('intasend/', webhooks.intasend_webhook, name='webhook-intasend'),
    path('mpesa/', webhooks.mpesa_webhook, name='webhook-mpesa'),
    path('stripe/', webhooks.stripe_webhook, name='webhook-stripe'),
]