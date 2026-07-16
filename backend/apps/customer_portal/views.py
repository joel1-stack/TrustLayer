from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Count
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.contrib import messages
from apps.agreements.models import Agreement
from apps.ledger.models import LedgerEntry
from apps.settlements.models import Settlement
from apps.admin_dashboard.models import LoginAttempt, AuditLogEntry
from .models import Customer, CustomerTeamMember, EmailVerificationToken


LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 30


def _check_customer_auth(request):
    return request.session.get('customer_authenticated')


def _get_failed_attempts(ip):
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
                LoginAttempt.objects.create(username=f'cust_{name}', ip_address=ip, success=False)
                error = 'Invalid credentials'
            elif not cust.password_hash:
                error = 'No password set. Contact your administrator.'
            elif cust.check_password(password):
                request.session['customer_authenticated'] = True
                request.session['customer_id'] = cust.customer_id
                request.session['customer_name'] = cust.name
                request.session['customer_email_verified'] = cust.email_verified
                request.session.set_expiry(1800)
                LoginAttempt.objects.create(username=f'cust_{name}', ip_address=ip, success=True)
                AuditLogEntry.objects.create(actor=f'customer:{name}', actor_ip=ip,
                    action='portal_login', resource_type='customer', resource_id=cust.customer_id)

                # If not verified, go to pending verification
                if not cust.email_verified:
                    return redirect('/portal/verify/pending/')
                return redirect('/portal/')
            else:
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


def verify_pending(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    customer_id = request.session.get('customer_id')
    cust = get_object_or_404(Customer, customer_id=customer_id)
    sent = request.GET.get('sent', '')
    return render(request, 'customer_portal/verify_pending.html', {
        'customer': cust, 'sent': sent,
    })


def verify_send_email(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    if request.method != 'POST':
        return redirect('/portal/verify/pending/')
    customer_id = request.session.get('customer_id')
    cust = get_object_or_404(Customer, customer_id=customer_id)

    if not cust.admin_email:
        return render(request, 'customer_portal/verify_pending.html', {
            'customer': cust, 'error': 'No email on file. Contact administrator.',
        })

    # Invalidate old tokens
    EmailVerificationToken.objects.filter(customer=cust, used=False).update(used=True)

    token = EmailVerificationToken.objects.create(customer=cust, email=cust.admin_email)
    verify_url = f'{settings.TRUSTLAYER_BASE_URL}/portal/verify/confirm/{token.token}/'

    # Build email content
    subject = 'Verify your TrustLayer account'
    message = f'Click this link to verify your email: {verify_url}'
    html_message = f'''
    <p>Hi {cust.name},</p>
    <p>Click the button below to verify your email and access your dashboard:</p>
    <p><a href="{verify_url}" style="display:inline-block;padding:12px 24px;background:#4f8cff;color:#fff;text-decoration:none;border-radius:8px;">Verify Account</a></p>
    <p>Or copy this link: <a href="{verify_url}">{verify_url}</a></p>
    <p>This link expires in 24 hours.</p>
    '''

    try:
        from django.core.mail import send_mail
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [cust.admin_email],
                  html_message=html_message, fail_silently=False)
        AuditLogEntry.objects.create(actor=f'customer:{cust.name}', action='verification_email_sent',
            resource_type='customer', resource_id=cust.customer_id,
            detail={'email': cust.admin_email, 'token': token.token[:16]})
    except Exception as e:
        print(f'Email send failed (configure email backend): {e}')

    return redirect('/portal/verify/pending/?sent=1')


def verify_confirm(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)

    if not token_obj.is_valid():
        return render(request, 'customer_portal/verify_result.html', {
            'success': False, 'message': 'This verification link has expired or already been used.',
        })

    token_obj.used = True
    token_obj.save()

    cust = token_obj.customer
    cust.email_verified = True
    cust.save()

    AuditLogEntry.objects.create(actor=f'customer:{cust.name}', action='email_verified',
        resource_type='customer', resource_id=cust.customer_id)

    # Log the user in by creating a fresh verified session
    request.session.flush()
    request.session['customer_authenticated'] = True
    request.session['customer_id'] = cust.customer_id
    request.session['customer_name'] = cust.name
    request.session['customer_email_verified'] = True
    request.session.set_expiry(1800)

    return redirect('/portal/')


def portal_home(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    customer_name = request.session.get('customer_name', '')
    if customer_name:
        qs = Agreement.objects.filter(creator_id=customer_name)
    else:
        qs = Agreement.objects.all()
    total_agreements = qs.count()
    from apps.constants import STATUS_CATEGORIES
    terminal_states = [s for s, c in STATUS_CATEGORIES.items() if c == 'terminal']
    active = qs.exclude(status__in=terminal_states).count()
    settled = qs.filter(status='SETTLED').count()
    total_collected = LedgerEntry.objects.filter(entry_type='CREDIT', agreement__in=qs).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_settled = Settlement.objects.filter(status='COMPLETED', agreement__in=qs).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    recent = qs.order_by('-created_at')[:10]
    return render(request, 'customer_portal/dashboard.html', {
        'total_agreements': total_agreements, 'active_agreements': active,
        'settled_count': settled, 'total_collected': total_collected, 'total_settled': total_settled,
        'recent_agreements': recent,
    })


def portal_agreements(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    customer_name = request.session.get('customer_name', '')
    if customer_name:
        agreements = Agreement.objects.filter(creator_id=customer_name).order_by('-created_at')[:50]
    else:
        agreements = Agreement.objects.all().order_by('-created_at')[:50]
    return render(request, 'customer_portal/agreements.html', {'agreements': agreements})


def portal_agreement_create(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    customer_id = request.session.get('customer_id')
    cust = get_object_or_404(Customer, customer_id=customer_id)
    if not cust.email_verified:
        return redirect('/portal/verify/pending/')

    error = ''
    success = ''
    payment_url = ''
    agreement_id = ''
    title = description = amount = ''
    buyer_name = buyer_phone = ''
    vendor_name = vendor_phone = ''
    delivery_name = delivery_phone = ''
    vendor_split = '90'
    delivery_split_raw = '0'

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '').strip()
        buyer_name = request.POST.get('buyer_name', '').strip()
        buyer_phone = request.POST.get('buyer_phone', '').strip()
        vendor_name = request.POST.get('vendor_name', '').strip()
        vendor_phone = request.POST.get('vendor_phone', '').strip()
        vendor_split = request.POST.get('vendor_split', '90').strip()
        delivery_name = request.POST.get('delivery_name', '').strip()
        delivery_phone = request.POST.get('delivery_phone', '').strip()
        delivery_split_raw = request.POST.get('delivery_split', '0').strip()

        if not title or not amount:
            error = 'Title and amount are required'
        elif not buyer_name:
            error = 'Buyer name is required'
        elif not buyer_phone:
            error = 'Buyer phone is required'
        elif not vendor_name:
            error = 'Vendor name is required'
        else:
            try:
                from decimal import Decimal, InvalidOperation
                amount_dec = Decimal(amount)
                v_split = Decimal(vendor_split)
            except (InvalidOperation, ValueError):
                error = 'Invalid amount or split value'
                amount_dec = None
                v_split = None

            if not error:
                platform_pct = Decimal(str(settings.TRUSTLAYER_PLATFORM_FEE_PERCENT))
                delivery_split = Decimal(delivery_split_raw) if delivery_name else Decimal('0')
                total = platform_pct + delivery_split + v_split
                if total != 100:
                    error = f'Splits must total 100% (currently {total}%)'
                else:
                    from apps.agreements.services import AgreementService
                    from apps.state_machine.services import StateMachine
                    from apps.payments.services import PaymentService

                    agreement = AgreementService.create_agreement(
                        title=title,
                        amount=amount_dec,
                        creator_id=cust.name,
                        description=description,
                        creator_type='customer',
                    )
                    agreement_id = agreement.agreement_id[:12]

                    AgreementService.add_party(agreement, role='BUYER', name=buyer_name, identifier=buyer_phone)
                    AgreementService.add_party(agreement, role='VENDOR', name=vendor_name, identifier=vendor_phone, split_percentage=v_split)
                    if delivery_name:
                        AgreementService.add_party(agreement, role='DELIVERY_AGENT', name=delivery_name, identifier=delivery_phone, split_percentage=delivery_split)

                    ip = request.META.get('REMOTE_ADDR', '')

                    StateMachine.transition(agreement, 'CONFIRMED', triggered_by='portal',
                        actor_role='customer_user', channel='portal', ip_address=ip,
                        reason='Agreement created via customer portal')

                    tx, result = PaymentService.generate_payment_link(agreement, phone=buyer_phone, provider='intasend')

                    if result.get('success'):
                        agreement.payment_url = result.get('payment_url', '')
                        agreement.save(update_fields=['payment_url'])
                        payment_url = result['payment_url']
                        StateMachine.transition(agreement, 'SUBMITTED', triggered_by='system',
                            actor_role='settlement_engine', channel='system', ip_address=ip,
                            provider_ref=result.get('provider_reference', ''),
                            reason=f'IntaSend checkout link generated: {payment_url[:40]}...')

                    AuditLogEntry.objects.create(actor=f'customer:{cust.name}',
                        action='agreement_created', resource_type='agreement', resource_id=agreement.agreement_id)
                    success = f'Agreement {agreement_id} created!'
                    title = description = amount = ''

    return render(request, 'customer_portal/agreement_create.html', {
        'error': error, 'success': success, 'payment_url': payment_url, 'agreement_id': agreement_id,
        'title': title, 'description': description, 'amount': amount,
        'buyer_name': buyer_name, 'buyer_phone': buyer_phone,
        'vendor_name': vendor_name, 'vendor_phone': vendor_phone,
        'delivery_name': delivery_name, 'delivery_phone': delivery_phone,
        'delivery_split': delivery_split_raw,
        'vendor_split': vendor_split,

    })


def portal_ledger(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    customer_name = request.session.get('customer_name', '')
    if customer_name:
        entries = LedgerEntry.objects.filter(agreement__creator_id=customer_name).order_by('-created_at')[:100]
    else:
        entries = LedgerEntry.objects.all().order_by('-created_at')[:100]
    return render(request, 'customer_portal/ledger.html', {'entries': entries})


def portal_settlements(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    customer_name = request.session.get('customer_name', '')
    if customer_name:
        settlements = Settlement.objects.filter(agreement__creator_id=customer_name).order_by('-created_at')[:100]
    else:
        settlements = Settlement.objects.all().order_by('-created_at')[:100]
    return render(request, 'customer_portal/settlements.html', {'settlements': settlements})


def portal_developers(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    return render(request, 'customer_portal/developers.html')


def portal_settings(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    customer_id = request.session.get('customer_id')
    cust = get_object_or_404(Customer, customer_id=customer_id)
    team = CustomerTeamMember.objects.filter(customer=cust).order_by('-created_at')

    error = ''
    success = ''
    if request.method == 'POST' and request.POST.get('action') == 'add_member':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', 'member').strip()
        password = request.POST.get('password', '')

        if not name or not email or not password:
            error = 'Name, email, and password are required'
        else:
            member = CustomerTeamMember(
                customer=cust, name=name, email=email,
                phone=phone, role=role,
            )
            member.set_password(password)
            member.save()
            AuditLogEntry.objects.create(actor=f'customer:{cust.name}',
                action='team_member_added', resource_type='customer_team', resource_id=member.member_id)
            success = f'Team member "{name}" added'

    return render(request, 'customer_portal/settings.html', {
        'team_members': team, 'error': error, 'success': success,
    })


def portal_toggle_member(request, member_id):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    if request.method != 'POST':
        return redirect('/portal/settings/')
    member = get_object_or_404(CustomerTeamMember, member_id=member_id)
    member.is_active = not member.is_active
    member.save()
    return redirect('/portal/settings/')


def portal_engines(request):
    if not _check_customer_auth(request):
        return redirect('/portal/login/')
    from apps.payments.adapters.registry import list_providers, get_adapter
    from apps.admin_dashboard.models import PlatformSettings
    all_s = {s.key: s.value for s in PlatformSettings.objects.all()}
    providers = []
    for p in list_providers():
        providers.append({'name': p.replace('_', ' ').title(), 'id': p})
    from apps.agreements.models import Agreement
    from apps.constants import STATUS_CODES
    customer_name = request.session.get('customer_name', '')
    state_counts = {}
    for s in ['CREATED', 'AVAILABLE', 'HELD', 'SETTLED']:
        if customer_name:
            c = Agreement.objects.filter(status=s, creator_id=customer_name).count()
        else:
            c = Agreement.objects.filter(status=s).count()
        if c:
            state_counts[f"{s} ({STATUS_CODES.get(s, '')})"] = c
    return render(request, 'customer_portal/engines.html', {
        'active': 'engines',
        'providers': providers,
        'state_counts': state_counts,
        'platform_fee': all_s.get('TRUSTLAYER_PLATFORM_FEE_PERCENT', '5.00'),
    })


def portal_contact(request):
    if request.method != 'POST':
        return redirect('/')
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    message = request.POST.get('message', '').strip()
    if not name or not email or not message:
        if request.headers.get('HX-Request'):
            return JsonResponse({'error': 'All fields required'}, status=400)
        return redirect('/?contact=failed')

    AuditLogEntry.objects.create(actor=f'contact:{name}', actor_ip=request.META.get('REMOTE_ADDR', ''),
        action='contact_form_submitted', resource_type='contact', detail={'email': email, 'message': message[:200]})

    try:
        from django.core.mail import send_mail
        subject = f'TrustLayer Contact from {name}'
        body = f'From: {name} <{email}>\nMessage:\n{message}'
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, ['help@trustlayer.com'], fail_silently=True)
    except Exception as e:
        print(f'Contact email send failed: {e}')

    if request.headers.get('HX-Request'):
        return JsonResponse({'success': True})
    return redirect('/?contact=sent')
