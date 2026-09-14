from django.contrib import admin
from .models import ContextRecord


@admin.register(ContextRecord)
class ContextRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'source_adapter', 'query_type', 'status', 'latency_ms', 'created_at')
    list_filter = ('status', 'source_adapter', 'query_type')
    search_fields = ('case__case_id', 'source_adapter', 'query_type')
    readonly_fields = ('created_at',)
