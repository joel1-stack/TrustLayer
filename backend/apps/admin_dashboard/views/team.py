from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from ..models import AdminUser, AuditLogEntry


def team_list(request):
    if not request.session.get('admin_authenticated'):
        return redirect('/admin/login/')
    members = AdminUser.objects.all().order_by('-created_at')
    return render(request, 'admin_dashboard/team.html', {'team_members': members, 'active_section': 'team'})


def team_create(request):
    if not request.session.get('admin_authenticated'):
        return redirect('/admin/login/')
    if request.session.get('admin_role') != 'owner':
        return redirect('/admin/team/')

    error = ''
    success = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            error = 'Username and password are required'
        elif AdminUser.objects.filter(username=username).exists():
            error = 'Username already exists'
        else:
            owner = AdminUser.objects.get(username=request.session['admin_username'])
            member = AdminUser(
                username=username,
                display_name=display_name or username,
                email=email,
                phone=phone,
                role='staff',
                created_by=owner,
            )
            member.set_password(password)
            member.save()
            AuditLogEntry.objects.create(actor=request.session['admin_username'],
                action='team_member_created', resource_type='admin_user', resource_id=member.username)
            success = f'Team member "{username}" created successfully'

    members = AdminUser.objects.all().order_by('-created_at')
    return render(request, 'admin_dashboard/team.html', {
        'team_members': members, 'error': error, 'success': success, 'active_section': 'team'
    })


def team_deactivate(request, username):
    if not request.session.get('admin_authenticated'):
        return redirect('/admin/login/')
    if request.session.get('admin_role') != 'owner':
        return redirect('/admin/team/')

    member = get_object_or_404(AdminUser, username=username)
    if member.role == 'owner':
        return redirect('/admin/team/')

    member.is_active = not member.is_active
    member.save()
    AuditLogEntry.objects.create(actor=request.session['admin_username'],
        action='team_member_deactivated' if not member.is_active else 'team_member_activated',
        resource_type='admin_user', resource_id=member.username)
    return redirect('/admin/team/')
