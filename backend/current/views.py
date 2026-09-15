from pathlib import Path

from django.contrib.auth import authenticate, login, logout
from django.http import FileResponse, Http404
from django.utils import timezone as django_timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Entry, Issue, User
from .serializers import AnnouncementUpdateSerializer, EntryCreateSerializer, EntrySerializer, IssueCreateSerializer, IssueSerializer, UserSerializer
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
    entry = Entry.objects.create(issue=issue, filename=data["file"].name, file=data["file"], page=data["page"], title=data["title"], origin=data["origin"], wordcount=data["wordcount"], description=data.get("description", ""), selector_name=request.user.username, status=Entry.Status.CREATED)
    audit("entries.create", request.user.username, f"创建投稿 {entry.uuid}")
    return Response(EntrySerializer(entry).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def review_entry(request, entry_uuid):
    if not request.user.has_perm("current.review_entry"):
        return Response({"detail": "没有审核投稿的权限。"}, status=status.HTTP_403_FORBIDDEN)
    try:
        entry = Entry.objects.get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if entry.status != Entry.Status.CREATED or not request.FILES.get("file"):
        return Response({"detail": "投稿当前不能审核，或缺少审核文件。"}, status=status.HTTP_400_BAD_REQUEST)
    entry.file = request.FILES["file"]
    entry.filename = request.FILES["file"].name
    entry.reviewer_name = request.user.username
    entry.status = Entry.Status.REVIEWED
    entry.save(update_fields=["file", "filename", "reviewer_name", "status", "updated_at"])
    audit("entries.review", request.user.username, f"审核投稿 {entry.uuid}")
    return Response(EntrySerializer(entry).data)


@api_view(["POST"])
def select_entry(request, entry_uuid):
    if not request.user.has_perm("current.select_entry"):
        return Response({"detail": "没有选录投稿的权限。"}, status=status.HTTP_403_FORBIDDEN)
    try:
        entry = Entry.objects.get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if entry.status not in (Entry.Status.REVIEWED, Entry.Status.SELECTED):
        return Response({"detail": "投稿尚未审核。"}, status=status.HTTP_400_BAD_REQUEST)
    entry.status = Entry.Status.REVIEWED if entry.status == Entry.Status.SELECTED else Entry.Status.SELECTED
    entry.save(update_fields=["status", "updated_at"])
    return Response(EntrySerializer(entry).data)


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
