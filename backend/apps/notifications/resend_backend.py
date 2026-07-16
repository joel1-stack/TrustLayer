import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        resend.api_key = settings.RESEND_API_KEY
        count = 0
        for message in email_messages:
            try:
                from_email = sanitize_address(message.from_email, message.encoding)
                to_emails = [sanitize_address(a, message.encoding) for a in message.recipients()]
                payload = {
                    "from": from_email,
                    "to": to_emails,
                    "subject": message.subject,
                    "text": message.body,
                }
                if message.alternatives:
                    for alt, alt_type in message.alternatives:
                        if alt_type == "text/html":
                            payload["html"] = alt
                resend.Emails.send(payload)
                count += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
        return count
