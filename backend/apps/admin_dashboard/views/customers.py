import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Sum
from django.contrib import messages
from apps.agreements.models import Agreement
from apps.customer_portal.models import Customer


def customer_list(request):
    customers = Customer.objects.all().order_by('-created_at')

    for c in customers:
        c.agreement_count = Agreement.objects.filter(creator_id=c.customer_id).count()

    return render(request, 'admin_dashboard/customers.html', {
        'customers': customers,
    })


def customer_detail(request, customer_id):
    customer = get_object_or_404(Customer, customer_id=customer_id)
    agreements = Agreement.objects.filter(creator_id=customer.customer_id).order_by('-created_at')[:50]
    return render(request, 'admin_dashboard/customer_detail.html', {
        'customer': customer,
        'agreements': agreements,
    })


def customer_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        industry = request.POST.get('industry', '').strip()
        admin_name = request.POST.get('admin_name', '').strip()
        admin_phone = request.POST.get('admin_phone', '').strip()
        admin_email = request.POST.get('admin_email', '').strip()
        password = request.POST.get('password', '').strip()
        if name:
            key = 'tl_live_' + secrets.token_hex(16)
            customer = Customer.objects.create(
                name=name,
                industry=industry,
                admin_name=admin_name,
                admin_phone=admin_phone,
                admin_email=admin_email,
                api_key=key,
                api_key_masked=key[:8] + '****' + key[-4:],
            )
            if password:
                customer.set_password(password)
                customer.save()
            from ..models import AuditLogEntry
            AuditLogEntry.objects.create(
                actor=request.session.get('admin_username', 'admin'),
                actor_ip=request.META.get('REMOTE_ADDR', ''),
                action='customer_created',
                resource_type='customer',
                resource_id=customer.customer_id,
                detail={'name': name, 'industry': industry},
            )
            messages.success(request, f'Customer {name} created successfully')
            return redirect(f'/admin/customers/{customer.customer_id}/')
        messages.error(request, 'Name is required')
    return render(request, 'admin_dashboard/customer_create.html')
