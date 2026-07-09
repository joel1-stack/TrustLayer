import uuid
from decimal import Decimal
from django.db import models


class Customer(models.Model):
    customer_id = models.CharField(max_length=36, unique=True, editable=False)
    name = models.CharField(max_length=256)
    industry = models.CharField(max_length=64, blank=True, default='')
    admin_name = models.CharField(max_length=128, blank=True, default='')
    admin_phone = models.CharField(max_length=32, blank=True, default='')
    admin_email = models.EmailField(blank=True, default='')
    api_key = models.CharField(max_length=128, unique=True, blank=True)
    api_key_masked = models.CharField(max_length=64, blank=True, default='')
    split_default = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'))
    password_hash = models.CharField(max_length=256, blank=True, default='')
    status = models.CharField(max_length=32, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    def set_password(self, raw):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw)

    def check_password(self, raw):
        from django.contrib.auth.hashers import check_password
        return check_password(raw, self.password_hash)

    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = str(uuid.uuid4())
        if not self.api_key:
            import secrets
            key = f'tl_live_{secrets.token_hex(16)}'
            self.api_key = key
            self.api_key_masked = key[:8] + '****' + key[-4:]
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'customer_tenant'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
