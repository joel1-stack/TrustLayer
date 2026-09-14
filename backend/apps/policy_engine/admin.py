from django.contrib import admin
from .models import PolicyRule, PolicyDecision


@admin.register(PolicyRule)
class PolicyRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'rule_id', 'name', 'action_type', 'required_clearance', 'risk_level', 'enabled', 'created_at')
    list_filter = ('enabled', 'required_clearance', 'risk_level', 'action_type')
    search_fields = ('rule_id', 'name')
    readonly_fields = ('created_at',)


@admin.register(PolicyDecision)
class PolicyDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'rule', 'decision', 'decided_by', 'decided_at')
    list_filter = ('decision',)
    search_fields = ('case__case_id', 'rule__rule_id')
    readonly_fields = ('decided_at',)
