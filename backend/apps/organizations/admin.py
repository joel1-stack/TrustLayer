from django.contrib import admin
from .models import Organization

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'org_type', 'status', 'integration_mode')
    list_filter = ('org_type', 'status', 'integration_mode')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
