"""
Shared auth decorator for all API views.
Checks for admin session OR valid API key.
"""
import json
from functools import wraps
from django.http import JsonResponse


def require_api_auth(view_func):
    @wraps(view_func)
    def _wrapper(request, *args, **kwargs):
        # Allow admin session (logged-in dashboard users)
        if request.session.get('admin_authenticated'):
            return view_func(request, *args, **kwargs)
        # Allow API key via X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY', '')
        if api_key:
            from apps.customer_portal.models import Customer
            if Customer.objects.filter(api_key=api_key, is_active=True).exists():
                return view_func(request, *args, **kwargs)
        # Allow valid sessionid cookie (Django admin)
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        return JsonResponse({'error': 'Authentication required. Provide session cookie or X-API-Key header.'}, status=401)
    return _wrapper
