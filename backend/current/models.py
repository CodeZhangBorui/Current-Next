import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    grade = models.PositiveSmallIntegerField("年级", default=0)
    classnum = models.PositiveSmallIntegerField("班级", default=0)
    legacy_password_hash = models.CharField("旧系统密码摘要", max_length=128, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"
        permissions = [("access_management", "访问 Current 管理功能")]


class Issue(models.Model):
    issue_number = models.PositiveIntegerField("期号", primary_key=True)
    deadline = models.DateTimeField("截稿时间")
    subject2 = models.CharField("第二版主题", max_length=255, blank=True)
    subject3 = models.CharField("第三版主题", max_length=255, blank=True)
    subject4 = models.CharField("第四版主题", max_length=255, blank=True)
    leader = models.ForeignKey("User", verbose_name="负责人", on_delete=models.SET_NULL, null=True, blank=True, related_name="led_issues")
    editors = models.ManyToManyField("User", verbose_name="审核编辑", blank=True, related_name="edited_issues")
    responsible_editor = models.ForeignKey("User", verbose_name="主编", on_delete=models.SET_NULL, null=True, blank=True, related_name="responsible_issues")
    published = models.BooleanField("已出版", default=False)
    pdf = models.FileField("报刊 PDF", upload_to="issues/", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    def __str__(self):
        return f"第 {self.issue_number} 期" if self.issue_number is not None else "未编号期刊"

    class Meta:
        ordering = ["-issue_number"]
        verbose_name = "期刊"
        verbose_name_plural = "期刊"
        permissions = [("create_issue", "创建期刊"), ("publish_issue", "发布期刊")]


class Entry(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待投稿"
        CREATED = "created", "已投稿"
        REVIEWED = "reviewed", "审核完成"
        SELECTED = "selected", "已合并"
        INVALID = "invalid", "已关闭：无效"

    uuid = models.CharField("稿件 ID", primary_key=True, max_length=128, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(Issue, verbose_name="所属期刊", on_delete=models.CASCADE, related_name="entries")
    filename = models.CharField("当前文件名", max_length=255, blank=True)
    file = models.FileField("当前文件", upload_to="entries/", blank=True)
    page = models.PositiveSmallIntegerField("版面")
    title = models.CharField("标题", max_length=255)
    origin = models.CharField("来源", max_length=255)
    wordcount = models.PositiveIntegerField("字数", default=0)
    description = models.TextField("投稿说明", blank=True)
    submitter = models.ForeignKey("User", verbose_name="投稿者", on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_entries")
    selector_name = models.CharField("旧系统选稿人记录", max_length=150, blank=True)
    reviewer_name = models.CharField("审核人记录", max_length=150, blank=True)
    review_completed_by = models.ForeignKey("User", verbose_name="完成审核者", on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_entry_reviews")
    review_completed_at = models.DateTimeField("审核完成时间", null=True, blank=True)
    merged_by = models.ForeignKey("User", verbose_name="合并者", on_delete=models.SET_NULL, null=True, blank=True, related_name="merged_entries")
    merged_at = models.DateTimeField("合并时间", null=True, blank=True)
    status = models.CharField("状态", max_length=16, choices=Status.choices, default=Status.PENDING)
    closed_from_status = models.CharField("关闭前状态", max_length=16, choices=Status.choices, blank=True)
    created_at = models.DateTimeField("投稿时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        issue_label = f"第 {self.issue_id} 期" if self.issue_id is not None else "未指定期刊"
        return f"{issue_label} · {self.title or '未命名稿件'}"

    class Meta:
        ordering = ["page", "created_at"]
        verbose_name = "稿件"
        verbose_name_plural = "稿件"
        permissions = [
            ("create_entry", "创建投稿"),
            ("review_entry", "审核稿件"),
            ("select_entry", "终审稿件"),
            ("remove_entry", "删除稿件"),
        ]


def entry_version_upload_to(instance, filename):
    safe_name = Path(filename).name
    return f"entry-versions/{instance.entry_id}/v{instance.version}/{safe_name}"


class EntryFileVersion(models.Model):
    class Source(models.TextChoices):
        SUBMISSION = "submission", "投稿"
        REVIEW = "review", "审核修订"
        LEGACY = "legacy", "旧系统导入"

    entry = models.ForeignKey(Entry, verbose_name="稿件", on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField("版本号")
    filename = models.CharField("文件名", max_length=255)
    file = models.FileField("文件", upload_to=entry_version_upload_to)
    uploader = models.ForeignKey("User", verbose_name="上传者", on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_entry_versions")
    uploader_name = models.CharField("上传者记录", max_length=150, blank=True)
    note = models.CharField("版本说明", max_length=500, blank=True)
    source = models.CharField("来源", max_length=16, choices=Source.choices, default=Source.REVIEW)
    created_at = models.DateTimeField("上传时间", auto_now_add=True)

    def __str__(self):
        entry_label = self.entry.title if self.entry_id else "未指定稿件"
        return f"{entry_label} · v{self.version or '?'}"

    class Meta:
        ordering = ["version"]
        verbose_name = "稿件文件版本"
        verbose_name_plural = "稿件文件版本"
        constraints = [models.UniqueConstraint(fields=("entry", "version"), name="unique_entry_file_version")]


class EntryComment(models.Model):
    entry = models.ForeignKey(Entry, verbose_name="稿件", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("User", verbose_name="留言者", on_delete=models.SET_NULL, null=True, blank=True, related_name="entry_comments")
    author_name = models.CharField("留言者记录", max_length=150, blank=True)
    body = models.TextField("留言内容", max_length=4000)
    created_at = models.DateTimeField("留言时间", auto_now_add=True)

    def __str__(self):
        return f"{self.author_name or '未知用户'}：{self.body[:30]}"

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "稿件留言"
        verbose_name_plural = "稿件留言"


class EntryStateEvent(models.Model):
    class Action(models.TextChoices):
        REVIEW_COMPLETED = "review_completed", "完成审核"
        REVIEW_RETURNED = "review_returned", "退回重新审核"
        CLOSED_INVALID = "closed_invalid", "关闭为无效"
        CLOSED_MERGED = "closed_merged", "关闭为已合并"
        REOPENED = "reopened", "重新打开"

    entry = models.ForeignKey(Entry, verbose_name="稿件", on_delete=models.CASCADE, related_name="state_events")
    action = models.CharField("操作", max_length=24, choices=Action.choices)
    actor = models.ForeignKey("User", verbose_name="操作人", on_delete=models.SET_NULL, null=True, blank=True, related_name="entry_state_events")
    actor_name = models.CharField("操作人记录", max_length=150, blank=True)
    from_status = models.CharField("原状态", max_length=16, choices=Entry.Status.choices, blank=True)
    to_status = models.CharField("新状态", max_length=16, choices=Entry.Status.choices)
    note = models.CharField("说明", max_length=500, blank=True)
    created_at = models.DateTimeField("操作时间", auto_now_add=True)

    def __str__(self):
        entry_label = self.entry.title if self.entry_id else "未指定稿件"
        return f"{entry_label} · {self.get_action_display()}"

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "稿件状态记录"
        verbose_name_plural = "稿件状态记录"


class SiteConfig(models.Model):
    key = models.CharField("配置键", max_length=100, unique=True)
    value = models.TextField("配置值", blank=True)
    value_type = models.CharField("值类型", max_length=16, default="str")

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = "站点配置"
        verbose_name_plural = "站点配置"


class AuditLog(models.Model):
    timestamp = models.DateTimeField("时间")
    scope = models.CharField("操作类型", max_length=100)
    executor = models.CharField("操作人", max_length=150, blank=True)
    message = models.TextField("内容")

    def __str__(self):
        timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M") if self.timestamp else "未记录时间"
        return f"{timestamp} · {self.executor or '系统'}"

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "审计日志"
        verbose_name_plural = "审计日志"


class ImportRun(models.Model):
    started_at = models.DateTimeField("开始时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    mode = models.CharField("导入模式", max_length=16)
    source_fingerprint = models.CharField("数据源指纹", max_length=64)
    report = models.JSONField("导入报告", default=dict)

    def __str__(self):
        started_at = self.started_at.strftime("%Y-%m-%d %H:%M") if self.started_at else "尚未开始"
        return f"导入 #{self.pk or '?'} · {started_at}"

    class Meta:
        verbose_name = "数据导入记录"
        verbose_name_plural = "数据导入记录"
