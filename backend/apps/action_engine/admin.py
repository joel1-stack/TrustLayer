from django.contrib import admin
from .models import ActionPlan, ActionResult


@admin.register(ActionPlan)
class ActionPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'action_type', 'priority', 'status', 'approved_by', 'created_at')
    list_filter = ('status', 'action_type')
    search_fields = ('case__case_id', 'action_type')
    readonly_fields = ('created_at',)


@admin.register(ActionResult)
class ActionResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'plan', 'outcome', 'duration_ms', 'executed_at')
    list_filter = ('outcome',)
    search_fields = ('plan__case__case_id',)
    readonly_fields = ('executed_at',)
