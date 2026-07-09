from django.core.management.base import BaseCommand
from apps.customer_portal.models import Customer


class Command(BaseCommand):
    help = 'Create a demo customer organization for testing'

    def handle(self, *args, **options):
        cust, created = Customer.objects.get_or_create(
            name='Demo Shop',
            defaults={
                'industry': 'Retail',
                'admin_name': 'John Demo',
                'admin_phone': '+254715641339',
                'admin_email': 'joelkaunda15@gmail.com',
                'status': 'active',
                'email_verified': True,
            }
        )
        if created:
            cust.set_password('demo123')
            cust.save()
            self.stdout.write(self.style.SUCCESS(f'Customer "Demo Shop" created'))
            self.stdout.write(f'  Organization: Demo Shop')
            self.stdout.write(f'  Password:      demo123')
        else:
            cust.set_password('demo123')
            cust.email_verified = True
            cust.save()
            self.stdout.write(self.style.SUCCESS(f'Customer "Demo Shop" updated'))

        self.stdout.write(self.style.SUCCESS('\nPortal login: /portal/login/'))
        self.stdout.write(f'  Name:     Demo Shop')
        self.stdout.write(f'  Password: demo123')
        self.stdout.write(f'\nAdmin login: /admin/login/')
        self.stdout.write(f'  Username: joelkaunda15')
        self.stdout.write(f'  Password: wherby')
