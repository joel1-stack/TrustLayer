from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect
from django.db.models import Sum, Count
from django.utils import timezone
from django.conf import settings
from apps.agreements.models import Agreement
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement
from .models import Customer


LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 30


def _check_customer_auth(request):
    return request.session.get('customer_authenticated')


def _get_failed_attempts(ip):
    from apps.admin_dashboard.models import LoginAttempt
    return LoginAttempt.objects.filter(
        ip_address=ip, success=False,
        timestamp__gte=timezone.now() - timedelta(minutes=LOGIN_LOCKOUT_MINUTES),
        username__startswith='cust_'
    ).count()


def portal_login(request):
    if _check_customer_auth(request):
        return redirect('/portal/')

    error = ''
    locked = False
    ip = request.META.get('REMOTE_ADDR', '')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        password = request.POST.get('password', '').strip()

        fails = _get_failed_attempts(ip)
        locked = fails >= LOGIN_MAX_ATTEMPTS

        if not locked:
            cust = Customer.objects.filter(name=name, status='active').first()
            if not cust:
                from apps.admin_dashboard.models import LoginAttempt
                LoginAttempt.objects.create(username=f'cust_{name}', ip_address=ip, success=False)
                error = 'Invalid credentials'
            elif not cust.password_hash:
                error = 'No password set. Contact your administrator.'
            elif cust.check_password(password):
                request.session['customer_authenticated'] = True
                request.session['customer_id'] = cust.customer_id
                request.session['customer_name'] = cust.name
                request.session.set_expiry(1800)
                from apps.admin_dashboard.models import LoginAttempt
                LoginAttempt.objects.create(username=f'cust_{name}', ip_address=ip, success=True)
                from apps.admin_dashboard.models import AuditLogEntry
                AuditLogEntry.objects.create(actor=f'customer:{name}', actor_ip=ip,
                    action='portal_login', resource_type='customer', resource_id=cust.customer_id)
                return redirect('/portal/')
            else:
                from apps.admin_dashboard.models import LoginAttempt
                LoginAttempt.objects.create(username=f'cust_{name}', ip_address=ip, success=False)
                error = 'Invalid credentials'
        else:
            error = f'Too many attempts. Try again in {LOGIN_LOCKOUT_MINUTES} minutes.'

    remaining = max(0, LOGIN_MAX_ATTEMPTS - _get_failed_attempts(ip))
    return render(request, 'customer_portal/login.html', {
        'error': error, 'locked': locked, 'remaining': remaining, 'lockout': LOGIN_LOCKOUT_MINUTES,
    })


def portal_logout(request):
    request.session.flush()
    return redirect('/portal/login/')


def portal_home(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    total_agreements = Agreement.objects.count()
    active = Agreement.objects.exclude(status__in=['SETTLED', 'REFUNDED', 'CANCELLED']).count()
    settled = Agreement.objects.filter(status='SETTLED').count()
    total_collected = LedgerEntry.objects.filter(entry_type='CREDIT').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_settled = Settlement.objects.filter(status='COMPLETED').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    recent = Agreement.objects.order_by('-created_at')[:10]
    return render(request, 'customer_portal/dashboard.html', {
        'total_agreements': total_agreements, 'active_agreements': active,
        'settled_count': settled, 'total_collected': total_collected, 'total_settled': total_settled,
        'recent_agreements': recent,
    })


def portal_agreements(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    agreements = Agreement.objects.all().order_by('-created_at')[:50]
    return render(request, 'customer_portal/agreements.html', {'agreements': agreements})


def portal_ledger(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    entries = LedgerEntry.objects.all().order_by('-created_at')[:100]
    return render(request, 'customer_portal/ledger.html', {'entries': entries})


def portal_settlements(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    settlements = Settlement.objects.all().order_by('-created_at')[:50]
    return render(request, 'customer_portal/settlements.html', {'settlements': settlements})


def portal_developers(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    return render(request, 'customer_portal/developers.html')


def portal_settings(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    return render(request, 'customer_portal/settings.html')
