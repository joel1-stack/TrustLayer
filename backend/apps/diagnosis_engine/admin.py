from django.contrib import admin
from .models import DiagnosisRecord


@admin.register(DiagnosisRecord)
class DiagnosisRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'root_cause', 'confidence', 'diagnosed_by', 'created_at')
    list_filter = ('diagnosed_by',)
    search_fields = ('case__case_id', 'root_cause')
    readonly_fields = ('created_at',)
