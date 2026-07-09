import json
from django.shortcuts import redirect
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.utils import timezone
from .models import LoginAttempt, AuditLogEntry


class IPWhitelistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            ip = request.META.get('REMOTE_ADDR', '')
            allowed = getattr(settings, 'ADMIN_ALLOWED_IPS', ['127.0.0.1'])
            if not request.session.get('admin_ip_whitelist_passed'):
                if ip not in allowed and '127.0.0.1' not in allowed:
                    return HttpResponseForbidden(json.dumps({'error': 'Access denied'}), content_type='application/json')
                request.session['admin_ip_whitelist_passed'] = True
        return self.get_response(request)


class AdminAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/') and request.path != '/admin/login/' and request.path != '/admin/static/' and not request.path.startswith('/admin/static/'):
            if not request.session.get('admin_authenticated'):
                return redirect('/admin/login/')
        return self.get_response(request)


class AdminAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/admin/') and request.session.get('admin_authenticated') and request.method == 'GET':
            try:
                if 'static' not in request.path and request.path not in ['/admin/login/', '/admin/logout/']:
                    AuditLogEntry.objects.create(
                        actor=request.session.get('admin_username', 'unknown'),
                        actor_ip=request.META.get('REMOTE_ADDR', ''),
                        action='viewed_page',
                        resource_type='page',
                        resource_id=request.path,
                        detail={'path': request.path, 'method': 'GET'},
                    )
            except Exception:
                pass
        return response
