from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def manifest_view(request):
    return JsonResponse({
        "name": "TrustLayer API",
        "version": "2.0.0",
        "description": "System of Action for Enterprise Operations. "
                       "Assemble context, diagnose problems, execute authorized actions, "
                       "and maintain complete operational truth.",
        "permissions": ["payments", "sms", "webhooks"],
        "environment": [
            {"key": "SECRET_KEY", "required": True, "description": "Django secret key"},
            {"key": "DB_HOST", "required": True, "description": "PostgreSQL host"},
            {"key": "DB_NAME", "required": True, "description": "PostgreSQL database name"},
            {"key": "DB_USER", "required": True, "description": "PostgreSQL user"},
            {"key": "DB_PASSWORD", "required": True, "description": "PostgreSQL password"},
            {"key": "REDIS_URL", "required": True, "description": "Redis connection URL"},
            {"key": "MPESA_CONSUMER_KEY", "required": False, "description": "M-Pesa Daraja consumer key"},
            {"key": "MPESA_CONSUMER_SECRET", "required": False, "description": "M-Pesa Daraja consumer secret"},
            {"key": "SMS_API_KEY", "required": False, "description": "Africa's Talking SMS API key"},
            {"key": "RESEND_API_KEY", "required": False, "description": "Resend transactional email API key"},
        ],
        "endpoints": [
            {"path": "/api/v1/agreements/", "method": "POST", "description": "Create case"},
            {"path": "/api/docs/", "method": "GET", "description": "Swagger API documentation"},
            {"path": "/health/", "method": "GET", "description": "Health check"},
            {"path": "/webhooks/mpesa/", "method": "POST", "description": "M-Pesa webhook receiver"},
        ],
        "category": "operations",
        "pricing": "free",
    })
