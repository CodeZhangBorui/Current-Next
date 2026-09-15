import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    grade = models.PositiveSmallIntegerField(default=0)
    classnum = models.PositiveSmallIntegerField(default=0)
    legacy_password_hash = models.CharField(max_length=128, blank=True)

    class Meta:
        permissions = [("access_management", "Can access Current management")]


class Issue(models.Model):
    issue_number = models.PositiveIntegerField(primary_key=True)
    deadline = models.DateTimeField()
    subject2 = models.CharField(max_length=255, blank=True)
    subject3 = models.CharField(max_length=255, blank=True)
    subject4 = models.CharField(max_length=255, blank=True)
    leader = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="led_issues")
    editors = models.ManyToManyField("User", blank=True, related_name="edited_issues")
    responsible_editor = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="responsible_issues")
    published = models.BooleanField(default=False)
    pdf = models.FileField(upload_to="issues/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issue_number"]
        permissions = [("create_issue", "Can create issues"), ("publish_issue", "Can publish issues")]


class Entry(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待投稿"
        CREATED = "created", "已投稿"
        REVIEWED = "reviewed", "已审核"
        SELECTED = "selected", "已选录"

    uuid = models.CharField(primary_key=True, max_length=128, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="entries")
    filename = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="entries/", blank=True)
    page = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=255)
    origin = models.CharField(max_length=255)
    wordcount = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    selector_name = models.CharField(max_length=150, blank=True)
    reviewer_name = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["page", "created_at"]
        permissions = [
            ("create_entry", "Can create entries"),
            ("review_entry", "Can review entries"),
            ("select_entry", "Can select entries"),
            ("remove_entry", "Can remove entries"),
        ]


class SiteConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    value_type = models.CharField(max_length=16, default="str")


class AuditLog(models.Model):
    timestamp = models.DateTimeField()
    scope = models.CharField(max_length=100)
    executor = models.CharField(max_length=150, blank=True)
    message = models.TextField()

    class Meta:
        ordering = ["-timestamp"]


class ImportRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    mode = models.CharField(max_length=16)
    source_fingerprint = models.CharField(max_length=64)
    report = models.JSONField(default=dict)
