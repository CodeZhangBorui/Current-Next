from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count
from django.utils.html import format_html

from .models import AuditLog, Entry, EntryComment, EntryFileVersion, EntryStateEvent, ImportRun, Issue, SiteConfig, User
from .signals import grant_default_permission


admin.site.site_header = "Current 内容管理"
admin.site.site_title = "Current 管理后台"
admin.site.index_title = "报刊与稿件管理"
admin.site.empty_value_display = "未填写"


STATUS_COLORS = {
    Entry.Status.PENDING: ("#64748b", "#f1f5f9"),
    Entry.Status.CREATED: ("#475569", "#f8fafc"),
    Entry.Status.REVIEWED: ("#1d4ed8", "#eff6ff"),
    Entry.Status.SELECTED: ("#15803d", "#f0fdf4"),
    Entry.Status.INVALID: ("#b91c1c", "#fef2f2"),
}


class EntryRelationInline(admin.TabularInline):
    extra = 0
    show_change_link = True


class EntryFileVersionInline(EntryRelationInline):
    model = EntryFileVersion
    fields = ("version", "filename", "file", "uploader", "uploader_name", "source", "note")
    autocomplete_fields = ("uploader",)


class EntryCommentInline(EntryRelationInline):
    model = EntryComment
    fields = ("author", "author_name", "body")
    autocomplete_fields = ("author",)


class EntryStateEventInline(EntryRelationInline):
    model = EntryStateEvent
    fields = ("action", "actor", "actor_name", "from_status", "to_status", "note")
    autocomplete_fields = ("actor",)


@admin.register(User)
class CurrentUserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("个人资料", {"fields": ("first_name", "last_name", "email", "grade", "classnum")}),
        ("账号状态与权限", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("重要日期", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2", "email", "grade", "classnum", "is_active", "is_staff"),
            },
        ),
    )
    list_display = ("username", "display_name", "grade", "classnum", "is_active", "is_staff", "last_login")
    list_filter = ("is_active", "is_staff", "is_superuser", "grade", "classnum")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    filter_horizontal = ("groups", "user_permissions")

    @admin.display(description="姓名")
    def display_name(self, obj):
        return obj.get_full_name() or "未填写"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        grant_default_permission(form.instance)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    fieldsets = (
        ("期刊信息", {"fields": ("issue_number", "deadline", "published", "pdf")}),
        ("版面主题", {"fields": ("subject2", "subject3", "subject4")}),
        ("编辑团队", {"fields": ("leader", "responsible_editor", "editors")}),
    )
    list_display = ("issue_number_label", "deadline", "publication_status", "entry_count", "leader", "responsible_editor")
    list_filter = ("published", "deadline")
    search_fields = ("=issue_number", "subject2", "subject3", "subject4", "leader__username", "responsible_editor__username", "editors__username")
    autocomplete_fields = ("leader", "responsible_editor", "editors")
    list_select_related = ("leader", "responsible_editor")
    date_hierarchy = "deadline"
    ordering = ("-issue_number",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_entry_count=Count("entries", distinct=True))

    @admin.display(description="期刊", ordering="issue_number")
    def issue_number_label(self, obj):
        return str(obj)

    @admin.display(description="出版状态", ordering="published")
    def publication_status(self, obj):
        color, background = ("#15803d", "#f0fdf4") if obj.published else ("#92400e", "#fffbeb")
        label = "已出版" if obj.published else "征稿中"
        return format_html(
            '<span style="color:{};background:{};padding:3px 8px;border-radius:4px;font-weight:600">{}</span>',
            color,
            background,
            label,
        )

    @admin.display(description="稿件数", ordering="_entry_count")
    def entry_count(self, obj):
        return obj._entry_count


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    fieldsets = (
        ("稿件信息", {"fields": ("issue", "page", "title", "origin", "wordcount", "description", "submitter")}),
        ("文件", {"fields": ("filename", "file")}),
        (
            "审核流程",
            {
                "fields": (
                    "status",
                    "review_completed_by",
                    "review_completed_at",
                    "merged_by",
                    "merged_at",
                    "closed_from_status",
                )
            },
        ),
        ("兼容记录", {"classes": ("collapse",), "fields": ("selector_name", "reviewer_name")}),
    )
    list_display = ("title", "issue", "page_label", "status_badge", "submitter", "review_completed_by", "merged_by", "updated_at")
    list_filter = ("status", "page", "issue")
    search_fields = ("title", "origin", "description", "filename", "submitter__username", "review_completed_by__username", "merged_by__username")
    autocomplete_fields = ("issue", "submitter", "review_completed_by", "merged_by")
    list_select_related = ("issue", "submitter", "review_completed_by", "merged_by")
    date_hierarchy = "created_at"
    ordering = ("-issue__issue_number", "page", "created_at")
    list_per_page = 50
    inlines = (EntryFileVersionInline, EntryCommentInline, EntryStateEventInline)

    @admin.display(description="版面", ordering="page")
    def page_label(self, obj):
        return f"第 {obj.page} 版"

    @admin.display(description="状态", ordering="status")
    def status_badge(self, obj):
        color, background = STATUS_COLORS.get(obj.status, ("#475569", "#f8fafc"))
        return format_html(
            '<span style="color:{};background:{};padding:3px 8px;border-radius:4px;font-weight:600">{}</span>',
            color,
            background,
            obj.get_status_display(),
        )


@admin.register(EntryFileVersion)
class EntryFileVersionAdmin(admin.ModelAdmin):
    list_display = ("entry", "version", "filename", "uploader", "uploader_name", "source", "created_at")
    list_filter = ("source", "created_at")
    search_fields = ("entry__title", "entry__uuid", "filename", "uploader__username", "uploader_name", "note")
    autocomplete_fields = ("entry", "uploader")
    list_select_related = ("entry", "uploader")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(EntryComment)
class EntryCommentAdmin(admin.ModelAdmin):
    list_display = ("entry", "author", "author_name", "comment_excerpt", "created_at")
    list_filter = ("created_at",)
    search_fields = ("entry__title", "entry__uuid", "author__username", "author_name", "body")
    autocomplete_fields = ("entry", "author")
    list_select_related = ("entry", "author")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(description="留言摘要")
    def comment_excerpt(self, obj):
        return obj.body[:60]


@admin.register(EntryStateEvent)
class EntryStateEventAdmin(admin.ModelAdmin):
    list_display = ("entry", "action", "actor", "actor_name", "from_status", "to_status", "created_at")
    list_filter = ("action", "from_status", "to_status", "created_at")
    search_fields = ("entry__title", "entry__uuid", "actor__username", "actor_name", "note")
    autocomplete_fields = ("entry", "actor")
    list_select_related = ("entry", "actor")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "value_type", "value_excerpt")
    list_filter = ("value_type",)
    search_fields = ("key", "value")
    ordering = ("key",)

    @admin.display(description="配置值摘要")
    def value_excerpt(self, obj):
        return obj.value[:80]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "scope", "executor", "message_excerpt")
    list_filter = ("scope", "timestamp")
    search_fields = ("scope", "executor", "message")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
    list_per_page = 100

    @admin.display(description="内容摘要")
    def message_excerpt(self, obj):
        return obj.message[:80]


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ("id", "mode", "started_at", "completed_at", "import_result", "source_fingerprint_short")
    list_filter = ("mode", "started_at", "completed_at")
    search_fields = ("source_fingerprint",)
    date_hierarchy = "started_at"
    ordering = ("-started_at",)

    @admin.display(description="结果")
    def import_result(self, obj):
        errors = obj.report.get("errors", []) if isinstance(obj.report, dict) else []
        return "成功" if obj.completed_at and not errors else ("有错误" if errors else "进行中")

    @admin.display(description="数据源指纹")
    def source_fingerprint_short(self, obj):
        return f"{obj.source_fingerprint[:12]}..." if len(obj.source_fingerprint) > 12 else obj.source_fingerprint
