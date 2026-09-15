from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, Entry, EntryComment, EntryFileVersion, EntryStateEvent, ImportRun, Issue, SiteConfig, User
from .signals import grant_default_permission


@admin.register(User)
class CurrentUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Current", {"fields": ("grade", "classnum")} ),)
    list_display = ("username", "grade", "classnum", "is_active", "is_staff")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        grant_default_permission(form.instance)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("issue_number", "deadline", "published")
    list_filter = ("published",)


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "issue", "page", "status", "selector_name", "reviewer_name")
    list_filter = ("status", "issue")
    search_fields = ("title", "origin", "selector_name", "reviewer_name")


@admin.register(EntryFileVersion)
class EntryFileVersionAdmin(admin.ModelAdmin):
    list_display = ("entry", "version", "filename", "uploader_name", "source", "created_at")
    list_filter = ("source", "created_at")
    search_fields = ("entry__title", "filename", "uploader_name")


@admin.register(EntryComment)
class EntryCommentAdmin(admin.ModelAdmin):
    list_display = ("entry", "author_name", "created_at")
    search_fields = ("entry__title", "author_name", "body")


@admin.register(EntryStateEvent)
class EntryStateEventAdmin(admin.ModelAdmin):
    list_display = ("entry", "action", "actor_name", "from_status", "to_status", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("entry__title", "actor_name", "note")


admin.site.register(SiteConfig)
admin.site.register(AuditLog)
admin.site.register(ImportRun)
