from django.contrib import admin
from .models import VerificationCheck, VerificationResult


@admin.register(VerificationCheck)
class VerificationCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'check_type', 'passed', 'checked_at')
    list_filter = ('passed', 'check_type')
    search_fields = ('case__case_id', 'check_type')
    readonly_fields = ('checked_at',)


@admin.register(VerificationResult)
class VerificationResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'overall_passed', 'checks_total', 'checks_passed', 'recovery_confirmed', 'verified_at')
    list_filter = ('overall_passed', 'recovery_confirmed')
    search_fields = ('case__case_id',)
    readonly_fields = ('verified_at',)
