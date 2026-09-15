from rest_framework import serializers

from .models import Entry, Issue, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "grade", "classnum", "is_active", "is_staff")


class IssueSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="issue_number", read_only=True)
    subject = serializers.SerializerMethodField()
    leader = UserSerializer(read_only=True, allow_null=True)
    editors = UserSerializer(many=True, read_only=True)
    responsible_editor = UserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Issue
        fields = ("id", "deadline", "subject", "leader", "editors", "responsible_editor", "published")

    def get_subject(self, obj):
        return [obj.subject2, obj.subject3, obj.subject4]


class EntrySerializer(serializers.ModelSerializer):
    issue_id = serializers.IntegerField(source="issue.issue_number", read_only=True)

    class Meta:
        model = Entry
        fields = ("uuid", "issue_id", "filename", "page", "title", "origin", "wordcount", "description", "selector_name", "reviewer_name", "status")


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
