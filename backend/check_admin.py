import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trustlayer.settings')
django.setup()
from apps.admin_dashboard.models import AdminUser, LoginAttempt
from django.utils import timezone
from datetime import timedelta
u = AdminUser.objects.get(username='joelkaunda15')
print('Active:', u.is_active)
print('Check wherby:', u.check_password('wherby'))
print('Recent fails (15 min):', LoginAttempt.objects.filter(success=False, timestamp__gte=timezone.now()-timedelta(minutes=15)).count())
