from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, Entry, ImportRun, Issue, LegacyPermission, LegacySession, LegacySudo, SiteConfig, User


@admin.register(User)
class CurrentUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Current", {"fields": ("grade", "classnum", "active")} ),)
    list_display = ("username", "grade", "classnum", "active", "is_staff")


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("issue_number", "deadline", "published")
    list_filter = ("published",)


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "issue", "page", "status", "selector_name", "reviewer_name")
    list_filter = ("status", "issue")
    search_fields = ("title", "origin", "selector_name", "reviewer_name")


admin.site.register(SiteConfig)
admin.site.register(AuditLog)
admin.site.register(LegacyPermission)
admin.site.register(ImportRun)
@admin.register(LegacySession)
class LegacySessionAdmin(admin.ModelAdmin):
    list_display = ("session", "username", "created_at")
    readonly_fields = ("session", "username", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LegacySudo)
class LegacySudoAdmin(admin.ModelAdmin):
    list_display = ("token", "username", "activity_at")
    readonly_fields = ("token", "username", "activity_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
