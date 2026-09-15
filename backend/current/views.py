from pathlib import Path

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone as django_timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Entry, EntryComment, EntryFileVersion, EntryStateEvent, Issue, User
from .permissions import can_comment_on_entry, is_entry_chief, is_entry_reviewer
from .serializers import AnnouncementUpdateSerializer, EntryCloseSerializer, EntryCommentCreateSerializer, EntryCreateSerializer, EntryReopenSerializer, EntryReviewSerializer, EntrySerializer, EntryVersionCreateSerializer, IssueCreateSerializer, IssueSerializer, UserSerializer
from .services import audit, get_config, set_config


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"detail": "CSRF cookie set."})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    user = authenticate(request, username=request.data.get("username"), password=request.data.get("password"))
    if not user or not user.is_active:
        return Response({"detail": "用户名或密码错误。"}, status=status.HTTP_401_UNAUTHORIZED)
    login(request, user)
    audit("auth.login", user.username, "用户登录")
    return Response({"user": UserSerializer(user).data})


@api_view(["GET"])
def me(request):
    return Response({"user": UserSerializer(request.user).data})


@api_view(["POST"])
def logout_view(request):
    audit("auth.logout", request.user.username, "用户退出登录")
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
def change_password(request):
    if not request.user.check_password(request.data.get("old_password", "")):
        return Response({"detail": "原密码错误。"}, status=status.HTTP_400_BAD_REQUEST)
    request.user.set_password(request.data.get("new_password", ""))
    request.user.save(update_fields=["password"])
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
def issues(request):
    if request.method == "GET":
        return Response(IssueSerializer(Issue.objects.all(), many=True).data)
    if not request.user.has_perm("current.create_issue"):
        return Response({"detail": "没有创建期刊的权限。"}, status=status.HTTP_403_FORBIDDEN)
    serializer = IssueCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    subjects = data["subject"]
    issue = Issue.objects.create(issue_number=data["id"], deadline=data["deadline"], subject2=subjects[0], subject3=subjects[1], subject4=subjects[2], leader=data.get("leader"), responsible_editor=data.get("responsible_editor"))
    issue.editors.set(data.get("editors", []))
    audit("issues.create", request.user.username, f"创建第 {issue.issue_number} 期")
    return Response(IssueSerializer(issue).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def user_choices(request):
    if not request.user.has_perm("current.create_issue"):
        return Response({"detail": "没有创建期刊的权限。"}, status=status.HTTP_403_FORBIDDEN)
    return Response(UserSerializer(User.objects.filter(is_active=True).order_by("username"), many=True).data)


@api_view(["GET"])
def issue_detail(request, issue_number):
    try:
        issue = Issue.objects.get(issue_number=issue_number)
    except Issue.DoesNotExist:
        return Response({"detail": "期刊不存在。"}, status=status.HTTP_404_NOT_FOUND)
    entries = EntrySerializer(issue.entries.all(), many=True).data
    return Response({"issue": IssueSerializer(issue).data, "entries": entries})


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def publish_issue(request, issue_number):
    if not request.user.has_perm("current.publish_issue"):
        return Response({"detail": "没有发布期刊的权限。"}, status=status.HTTP_403_FORBIDDEN)
    try:
        issue = Issue.objects.get(issue_number=issue_number)
    except Issue.DoesNotExist:
        return Response({"detail": "期刊不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if issue.published:
        return Response({"detail": "期刊已经发布。"}, status=status.HTTP_400_BAD_REQUEST)
    if request.FILES.get("pdf"):
        issue.pdf = request.FILES["pdf"]
    issue.published = True
    issue.save(update_fields=["pdf", "published"])
    audit("issues.publish", request.user.username, f"发布第 {issue.issue_number} 期")
    return Response(IssueSerializer(issue).data)


@api_view(["GET"])
def issue_pdf(request, issue_number):
    try:
        issue = Issue.objects.get(issue_number=issue_number)
    except Issue.DoesNotExist:
        raise Http404
    if not issue.published or not issue.pdf:
        return Response({"detail": "期刊 PDF 不可用。"}, status=status.HTTP_404_NOT_FOUND)
    return FileResponse(issue.pdf.open("rb"), as_attachment=False, filename=f"第{issue.issue_number}期.pdf")


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def entries(request, issue_number):
    if not request.user.has_perm("current.create_entry"):
        return Response({"detail": "没有创建投稿的权限。"}, status=status.HTTP_403_FORBIDDEN)
    try:
        issue = Issue.objects.get(issue_number=issue_number)
    except Issue.DoesNotExist:
        return Response({"detail": "期刊不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if issue.published:
        return Response({"detail": "期刊已经发布。"}, status=status.HTTP_400_BAD_REQUEST)
    serializer = EntryCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    entry = Entry.objects.create(issue=issue, filename=data["file"].name, file=data["file"], page=data["page"], title=data["title"], origin=data["origin"], wordcount=data["wordcount"], description=data.get("description", ""), submitter=request.user, selector_name=request.user.username, status=Entry.Status.CREATED)
    EntryFileVersion.objects.create(entry=entry, version=1, filename=entry.filename, file=entry.file.name, uploader=request.user, uploader_name=request.user.username, source=EntryFileVersion.Source.SUBMISSION, note="投稿者上传的初始版本")
    audit("entries.create", request.user.username, f"创建投稿 {entry.uuid}")
    return Response(EntrySerializer(entry).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def entry_review_detail(request, entry_uuid):
    try:
        entry = Entry.objects.select_related("issue", "issue__leader", "issue__responsible_editor", "submitter", "review_completed_by", "merged_by").prefetch_related("issue__editors", "versions__uploader", "comments__author", "state_events__actor").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    return Response(EntryReviewSerializer(entry, context={"request": request}).data)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_entry_version(request, entry_uuid):
    try:
        entry = Entry.objects.select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not is_entry_reviewer(request.user, entry):
        return Response({"detail": "没有上传审核版本的权限。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status != Entry.Status.CREATED or entry.issue.published:
        return Response({"detail": "稿件当前不能再上传审核版本。"}, status=status.HTTP_400_BAD_REQUEST)
    serializer = EntryVersionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        entry = Entry.objects.select_for_update().get(uuid=entry_uuid)
        latest = entry.versions.order_by("-version").first()
        version_number = latest.version + 1 if latest else 1
        uploaded_file = serializer.validated_data["file"]
        version = EntryFileVersion.objects.create(
            entry=entry,
            version=version_number,
            filename=uploaded_file.name,
            file=uploaded_file,
            uploader=request.user,
            uploader_name=request.user.username,
            source=EntryFileVersion.Source.REVIEW,
            note=serializer.validated_data.get("note", ""),
        )
        entry.file = version.file.name
        entry.filename = version.filename
        entry.save(update_fields=["file", "filename", "updated_at"])
    audit("entries.version.create", request.user.username, f"为投稿 {entry.uuid} 上传 v{version.version}")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def add_entry_comment(request, entry_uuid):
    try:
        entry = Entry.objects.select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not can_comment_on_entry(request.user, entry) or entry.status in (Entry.Status.SELECTED, Entry.Status.INVALID):
        return Response({"detail": "没有在此稿件留言的权限。"}, status=status.HTTP_403_FORBIDDEN)
    serializer = EntryCommentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    comment = EntryComment.objects.create(entry=entry, author=request.user, author_name=request.user.username, body=serializer.validated_data["body"])
    audit("entries.comment.create", request.user.username, f"在投稿 {entry.uuid} 留言")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def complete_entry_review(request, entry_uuid):
    try:
        entry = Entry.objects.select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not is_entry_reviewer(request.user, entry):
        return Response({"detail": "没有完成审核的权限。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status != Entry.Status.CREATED or not entry.versions.exists():
        return Response({"detail": "稿件当前不能标记为审核完成。"}, status=status.HTTP_400_BAD_REQUEST)
    entry.status = Entry.Status.REVIEWED
    entry.reviewer_name = request.user.username
    entry.review_completed_by = request.user
    entry.review_completed_at = django_timezone.now()
    entry.save(update_fields=["status", "reviewer_name", "review_completed_by", "review_completed_at", "updated_at"])
    EntryStateEvent.objects.create(entry=entry, action=EntryStateEvent.Action.REVIEW_COMPLETED, actor=request.user, actor_name=request.user.username, from_status=Entry.Status.CREATED, to_status=Entry.Status.REVIEWED)
    audit("entries.review.complete", request.user.username, f"完成投稿 {entry.uuid} 的审核")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data)


def _close_entry(entry, user, disposition, note=""):
    from_status = entry.status
    to_status = Entry.Status.SELECTED if disposition == "merged" else Entry.Status.INVALID
    entry.closed_from_status = from_status
    entry.status = to_status
    update_fields = ["closed_from_status", "status", "updated_at"]
    if disposition == "merged":
        entry.merged_by = user
        entry.merged_at = django_timezone.now()
        update_fields.extend(("merged_by", "merged_at"))
    entry.save(update_fields=update_fields)
    EntryStateEvent.objects.create(
        entry=entry,
        action=EntryStateEvent.Action.CLOSED_MERGED if disposition == "merged" else EntryStateEvent.Action.CLOSED_INVALID,
        actor=user,
        actor_name=user.username,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )


@api_view(["POST"])
def close_entry(request, entry_uuid):
    try:
        entry = Entry.objects.select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not is_entry_chief(request.user, entry):
        return Response({"detail": "只有主编级用户可以关闭稿件。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status not in (Entry.Status.CREATED, Entry.Status.REVIEWED) or entry.issue.published:
        return Response({"detail": "稿件当前不能关闭。"}, status=status.HTTP_400_BAD_REQUEST)
    serializer = EntryCloseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    disposition = serializer.validated_data["disposition"]
    if disposition == "merged" and entry.status != Entry.Status.REVIEWED:
        return Response({"detail": "只有已完成审核的稿件可以 Close as merged。"}, status=status.HTTP_400_BAD_REQUEST)
    _close_entry(entry, request.user, disposition, serializer.validated_data.get("note", ""))
    audit(f"entries.close.{disposition}", request.user.username, f"关闭投稿 {entry.uuid}")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data)


@api_view(["POST"])
def merge_entry(request, entry_uuid):
    try:
        entry = Entry.objects.select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not is_entry_chief(request.user, entry):
        return Response({"detail": "只有主编级用户可以合并稿件。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status != Entry.Status.REVIEWED or entry.issue.published:
        return Response({"detail": "只有已完成审核的稿件可以 Close as merged。"}, status=status.HTTP_400_BAD_REQUEST)
    _close_entry(entry, request.user, "merged")
    audit("entries.close.merged", request.user.username, f"关闭并合并投稿 {entry.uuid}")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data)


@api_view(["POST"])
def reopen_entry(request, entry_uuid):
    try:
        entry = Entry.objects.select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not is_entry_chief(request.user, entry):
        return Response({"detail": "只有主编级用户可以重新打开稿件。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status not in (Entry.Status.SELECTED, Entry.Status.INVALID) or entry.issue.published:
        return Response({"detail": "稿件当前不是可重新打开的关闭状态。"}, status=status.HTTP_400_BAD_REQUEST)
    serializer = EntryReopenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    from_status = entry.status
    restored_status = entry.closed_from_status if entry.closed_from_status in (Entry.Status.CREATED, Entry.Status.REVIEWED) else (Entry.Status.REVIEWED if from_status == Entry.Status.SELECTED else Entry.Status.CREATED)
    entry.status = restored_status
    entry.closed_from_status = ""
    update_fields = ["status", "closed_from_status", "updated_at"]
    if from_status == Entry.Status.SELECTED:
        entry.merged_by = None
        entry.merged_at = None
        update_fields.extend(("merged_by", "merged_at"))
    entry.save(update_fields=update_fields)
    EntryStateEvent.objects.create(entry=entry, action=EntryStateEvent.Action.REOPENED, actor=request.user, actor_name=request.user.username, from_status=from_status, to_status=restored_status, note=serializer.validated_data.get("note", ""))
    audit("entries.reopen", request.user.username, f"重新打开投稿 {entry.uuid}")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data)


@api_view(["DELETE"])
def remove_entry(request, entry_uuid):
    if not request.user.has_perm("current.remove_entry"):
        return Response({"detail": "没有删除投稿的权限。"}, status=status.HTTP_403_FORBIDDEN)
    deleted, _ = Entry.objects.filter(uuid=entry_uuid).delete()
    if not deleted:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def entry_file(request, entry_uuid):
    try:
        entry = Entry.objects.get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        raise Http404
    if not entry.file:
        raise Http404
    return FileResponse(entry.file.open("rb"), as_attachment=True, filename=entry.filename or Path(entry.file.name).name)


@api_view(["GET"])
def entry_version_file(request, entry_uuid, version_number):
    try:
        version = EntryFileVersion.objects.get(entry_id=entry_uuid, version=version_number)
    except EntryFileVersion.DoesNotExist:
        raise Http404
    return FileResponse(version.file.open("rb"), as_attachment=True, filename=version.filename)


@api_view(["GET"])
def announcement(request):
    return Response({
        "content": get_config("site.announcement", ""),
        "published_at": get_config("site.announcement_published_at", ""),
        "has_pdf": bool(get_config("site.announcementpdf", "")),
    })


@api_view(["GET", "POST"])
def manage_announcement(request):
    if not request.user.is_staff:
        return Response({"detail": "仅管理员可以管理公告。"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        return Response({
            "draft": get_config("site.announcement_draft", get_config("site.announcement", "")),
            "published": get_config("site.announcement", ""),
            "published_at": get_config("site.announcement_published_at", ""),
            "published_by": get_config("site.announcement_published_by", ""),
        })

    serializer = AnnouncementUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    content = serializer.validated_data["content"]
    set_config("site.announcement_draft", content)
    if serializer.validated_data["action"] == "save":
        audit("announcement.save", request.user.username, "保存公告草稿")
        return Response({"draft": content, "detail": "公告草稿已保存。"})

    published_at = django_timezone.now().isoformat()
    set_config("site.announcement", content)
    set_config("site.announcement_published_at", published_at)
    set_config("site.announcement_published_by", request.user.username)
    audit("announcement.publish", request.user.username, "发布站点公告")
    return Response({"content": content, "published_at": published_at, "published_by": request.user.username, "detail": "公告已发布。"})
