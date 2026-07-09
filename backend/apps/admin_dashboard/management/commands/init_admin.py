from django.core.management.base import BaseCommand
from apps.admin_dashboard.models import AdminUser
from apps.admin_dashboard.models import PlatformSettings


class Command(BaseCommand):
    help = 'Initialize the platform admin user and security settings'

    def handle(self, *args, **options):
        admin, created = AdminUser.objects.get_or_create(
            username='joelkaunda15',
            defaults={
                'display_name': 'Joel Stack',
                'email': 'joelkaunda15@gmail.com',
                'phone': '+254715641339',
                'role': 'owner',
                'is_active': True,
            }
        )
        if created:
            admin.set_password('wherby')
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Admin user "joelkaunda15" created'))
        else:
            admin.set_password('wherby')
            admin.email = 'joelkaunda15@gmail.com'
            admin.phone = '+254715641339'
            admin.role = 'owner'
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Admin user "joelkaunda15" updated'))

        PlatformSettings.objects.get_or_create(key='security_alert_email', defaults={
            'value': 'joelkaunda15@gmail.com', 'description': 'Email for security alerts'
        })
        PlatformSettings.objects.get_or_create(key='security_alert_phone', defaults={
            'value': '+254715641339', 'description': 'Phone for security/SMS alerts'
        })
        self.stdout.write(self.style.SUCCESS('Platform security settings configured'))
