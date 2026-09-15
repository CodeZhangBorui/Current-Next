from rest_framework import serializers

from .models import Entry, EntryComment, EntryFileVersion, EntryStateEvent, Issue, User
from .permissions import can_comment_on_entry, can_manage_issue_pdf, is_entry_chief, is_entry_reviewer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "grade", "classnum", "is_active", "is_staff")


class EntryFileVersionSerializer(serializers.ModelSerializer):
    uploader = UserSerializer(read_only=True, allow_null=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = EntryFileVersion
        fields = ("id", "version", "filename", "uploader", "uploader_name", "note", "source", "created_at", "download_url")

    def get_download_url(self, obj):
        return f"/api/v1/entries/{obj.entry_id}/versions/{obj.version}/file"


class EntryCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = EntryComment
        fields = ("id", "author", "author_name", "body", "created_at")


class EntryStateEventSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = EntryStateEvent
        fields = ("id", "action", "actor", "actor_name", "from_status", "to_status", "note", "created_at")


class IssueSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="issue_number", read_only=True)
    subject = serializers.SerializerMethodField()
    leader = UserSerializer(read_only=True, allow_null=True)
    editors = UserSerializer(many=True, read_only=True)
    responsible_editor = UserSerializer(read_only=True, allow_null=True)
    pdf_available = serializers.SerializerMethodField()
    can_manage_pdf = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = ("id", "deadline", "subject", "leader", "editors", "responsible_editor", "published", "pdf_available", "can_manage_pdf")

    def get_subject(self, obj):
        return [obj.subject2, obj.subject3, obj.subject4]

    def get_pdf_available(self, obj):
        return bool(obj.pdf)

    def get_can_manage_pdf(self, obj):
        request = self.context.get("request")
        return bool(request and can_manage_issue_pdf(request.user, obj))


class EntrySerializer(serializers.ModelSerializer):
    issue_id = serializers.IntegerField(source="issue.issue_number", read_only=True)
    submitter = UserSerializer(read_only=True, allow_null=True)
    review_completed_by = UserSerializer(read_only=True, allow_null=True)
    merged_by = UserSerializer(read_only=True, allow_null=True)
    version_count = serializers.IntegerField(source="versions.count", read_only=True)
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)

    class Meta:
        model = Entry
        fields = ("uuid", "issue_id", "filename", "page", "title", "origin", "wordcount", "description", "submitter", "selector_name", "reviewer_name", "status", "closed_from_status", "review_completed_by", "review_completed_at", "merged_by", "merged_at", "version_count", "comment_count", "created_at", "updated_at")


class EntryReviewSerializer(EntrySerializer):
    versions = EntryFileVersionSerializer(many=True, read_only=True)
    comments = EntryCommentSerializer(many=True, read_only=True)
    state_events = EntryStateEventSerializer(many=True, read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta(EntrySerializer.Meta):
        fields = EntrySerializer.Meta.fields + ("versions", "comments", "state_events", "capabilities")

    def get_capabilities(self, obj):
        user = self.context["request"].user
        return {
            "can_comment": can_comment_on_entry(user, obj) and obj.status not in (Entry.Status.SELECTED, Entry.Status.INVALID),
            "can_upload_version": is_entry_reviewer(user, obj) and obj.status == Entry.Status.CREATED and not obj.issue.published,
            "can_complete_review": is_entry_reviewer(user, obj) and obj.status == Entry.Status.CREATED and obj.versions.exists(),
            "can_return_to_review": is_entry_chief(user, obj) and obj.status == Entry.Status.REVIEWED,
            "can_merge": is_entry_chief(user, obj) and obj.status == Entry.Status.REVIEWED and not obj.issue.published,
            "can_close": is_entry_chief(user, obj) and obj.status in (Entry.Status.CREATED, Entry.Status.REVIEWED),
            "can_reopen": is_entry_chief(user, obj) and obj.status in (Entry.Status.SELECTED, Entry.Status.INVALID),
            "can_delete": user.has_perm("current.remove_entry"),
        }


class IssueCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    deadline = serializers.DateTimeField()
    subject = serializers.ListField(child=serializers.CharField(), min_length=3, max_length=3)
    leader_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), source="leader", required=False, allow_null=True)
    editor_ids = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), source="editors", many=True, required=False)
    responsible_editor_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), source="responsible_editor", required=False, allow_null=True)


class EntryCreateSerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, max_value=4)
    title = serializers.CharField(max_length=255)
    origin = serializers.CharField(max_length=255)
    wordcount = serializers.IntegerField(min_value=1)
    description = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField()


class EntryVersionCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class EntryCommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000, trim_whitespace=True)


class EntryCloseSerializer(serializers.Serializer):
    disposition = serializers.ChoiceField(choices=("invalid", "merged"))
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)


class EntryReopenSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)


class AnnouncementUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("save", "publish"))
    content = serializers.CharField(max_length=4000, allow_blank=True, trim_whitespace=True)
