from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, Entry, ImportRun, Issue, SiteConfig, User


@admin.register(User)
class CurrentUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Current", {"fields": ("grade", "classnum")} ),)
    list_display = ("username", "grade", "classnum", "is_active", "is_staff")


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
admin.site.register(ImportRun)
