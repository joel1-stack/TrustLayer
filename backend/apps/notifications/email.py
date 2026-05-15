from django.core.mail import send_mail
from django.conf import settings


class EmailService:
    @staticmethod
    def send(to_email, subject, body):
        try:
            send_mail(subject, body, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@trustlayer.app'), [to_email], fail_silently=False)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
