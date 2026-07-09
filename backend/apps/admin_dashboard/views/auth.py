from datetime import timedelta
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from ..models import AdminUser, LoginAttempt, AuditLogEntry, SecurityAlert
from apps.notifications.alert_service import check_and_alert_brute_force


LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15


def login_view(request):
    if request.session.get('admin_authenticated'):
        return redirect('/admin/dashboard/')

    error = ''
    locked = False
    ip = request.META.get('REMOTE_ADDR', '')
    ua = request.META.get('HTTP_USER_AGENT', '')

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        recent_fails = LoginAttempt.objects.filter(
            ip_address=ip, success=False,
            timestamp__gte=timezone.now() - timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        ).count()

        if recent_fails >= LOGIN_MAX_ATTEMPTS:
            LoginAttempt.objects.create(username=username, ip_address=ip, success=False, user_agent=ua)
            locked = True
            AuditLogEntry.objects.create(actor='system', actor_ip=ip, action='login_locked',
                resource_type='auth', detail={'username': username, 'reason': 'too_many_attempts'})
            check_and_alert_brute_force(ip, username)
        else:
            try:
                admin = AdminUser.objects.get(username=username, is_active=True)
                if admin.check_password(password):
                    admin.last_login = timezone.now()
                    admin.last_login_ip = ip
                    admin.save()
                    request.session['admin_authenticated'] = True
                    request.session['admin_username'] = admin.username
                    request.session['admin_display_name'] = admin.display_name
                    request.session['admin_role'] = admin.role
                    request.session['admin_login_time'] = timezone.now().isoformat()
                    request.session.set_expiry(1800)
                    LoginAttempt.objects.create(username=username, ip_address=ip, success=True, user_agent=ua)
                    AuditLogEntry.objects.create(actor=admin.username, actor_ip=ip,
                        action='login_success', resource_type='auth', detail={'username': username})
                    return redirect('/admin/dashboard/')
                else:
                    LoginAttempt.objects.create(username=username, ip_address=ip, success=False, user_agent=ua)
                    error = 'Invalid credentials'
                    AuditLogEntry.objects.create(actor='system', actor_ip=ip,
                        action='login_failed', resource_type='auth', detail={'username': username, 'reason': 'wrong_password'})
                    check_and_alert_brute_force(ip, username)
            except AdminUser.DoesNotExist:
                LoginAttempt.objects.create(username=username, ip_address=ip, success=False, user_agent=ua)
                error = 'Invalid credentials'

    failed_attempts = LoginAttempt.objects.filter(ip_address=ip, success=False,
        timestamp__gte=timezone.now() - timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).count()
    remaining = max(0, LOGIN_MAX_ATTEMPTS - failed_attempts)

    return render(request, 'admin_dashboard/login.html', {
        'error': error,
        'locked': locked,
        'remaining': remaining,
        'lockout_minutes': LOGIN_LOCKOUT_MINUTES,
    })


def logout_view(request):
    AuditLogEntry.objects.create(
        actor=request.session.get('admin_username', 'unknown'),
        actor_ip=request.META.get('REMOTE_ADDR', ''),
        action='logout', resource_type='auth')
    request.session.flush()
    return redirect('/admin/login/')
