from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import AuditLog, Notification, SystemSetting, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_sample")
    list_filter = ("role", "is_active", "is_sample")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = DjangoUserAdmin.fieldsets + (("Role", {"fields": ("role", "phone", "is_sample")}),)


admin.site.register(AuditLog)
admin.site.register(Notification)
admin.site.register(SystemSetting)
