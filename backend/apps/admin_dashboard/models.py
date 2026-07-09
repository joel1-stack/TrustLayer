import hashlib, uuid, json
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings


class AdminUser(models.Model):
    username = models.CharField(max_length=64, unique=True)
    password_hash = models.CharField(max_length=256)
    display_name = models.CharField(max_length=128, default='Operator')
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw):
        self.password_hash = make_password(raw)

    def check_password(self, raw):
        return check_password(raw, self.password_hash)

    class Meta:
        db_table = 'admin_user'
        verbose_name = 'Admin User'
        verbose_name_plural = 'Admin Users'


class LoginAttempt(models.Model):
    username = models.CharField(max_length=128)
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'admin_login_attempt'
        indexes = [models.Index(fields=['ip_address', 'timestamp'])]


class AuditLogEntry(models.Model):
    entry_id = models.CharField(max_length=36, unique=True, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=64)
    actor_ip = models.GenericIPAddressField(null=True, blank=True)
    action = models.CharField(max_length=128)
    resource_type = models.CharField(max_length=64, blank=True, default='')
    resource_id = models.CharField(max_length=64, blank=True, default='')
    detail = models.JSONField(default=dict, blank=True)
    previous_hash = models.CharField(max_length=64, blank=True, default='')
    hash = models.CharField(max_length=64, unique=True, editable=False)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = timezone.now()
        last = AuditLogEntry.objects.order_by('-timestamp').first()
        self.previous_hash = last.hash if last else '0' * 64
        raw = f'{self.entry_id}|{self.timestamp.isoformat()}|{self.actor}|{self.action}|{self.previous_hash}'
        self.hash = hashlib.sha256(raw.encode()).hexdigest()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'admin_audit_log'
        ordering = ['-timestamp']


class BackupRecord(models.Model):
    backup_id = models.CharField(max_length=36, unique=True, editable=False)
    label = models.CharField(max_length=128, blank=True, default='')
    backup_type = models.CharField(max_length=32, default='manual')
    size_bytes = models.BigIntegerField(default=0)
    file_path = models.CharField(max_length=512, blank=True, default='')
    sha256_hash = models.CharField(max_length=64, blank=True, default='')
    status = models.CharField(max_length=32, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)
    record_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.backup_id:
            self.backup_id = str(uuid.uuid4())
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'admin_backup_record'
        ordering = ['-created_at']


class PlatformSettings(models.Model):
    key = models.CharField(max_length=128, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=256, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_platform_settings'

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_decimal(cls, key, default=Decimal('0')):
        val = cls.get(key)
        if val is None:
            return default
        try:
            return Decimal(val)
        except Exception:
            return default

    @classmethod
    def get_int(cls, key, default=0):
        val = cls.get(key)
        if val is None:
            return default
        try:
            return int(val)
        except Exception:
            return default
