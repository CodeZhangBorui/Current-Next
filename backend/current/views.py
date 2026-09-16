from pathlib import Path

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404
from django.utils import timezone as django_timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Entry, EntryComment, EntryFileVersion, EntryStateEvent, Issue, User
from .permissions import can_comment_on_entry, can_manage_issue_pdf, is_entry_chief, is_entry_reviewer
from .serializers import AnnouncementUpdateSerializer, EntryCloseSerializer, EntryCommentCreateSerializer, EntryCreateSerializer, EntryReopenSerializer, EntryReviewSerializer, EntrySerializer, EntryVersionCreateSerializer, IssueCreateSerializer, IssueSerializer, UserSerializer
from .services import audit, get_config, set_config
from .validators import validate_pdf_upload


def _average_hours(rows, start_key, end_key):
    durations = [
        (row[end_key] - row[start_key]).total_seconds() / 3600
        for row in rows
        if row[start_key] and row[end_key] and row[end_key] >= row[start_key]
    ]
    return round(sum(durations) / len(durations), 4) if durations else None


@api_view(["GET"])
def statistics(request):
    ranking_period = request.query_params.get("ranking_period", "all")
    if ranking_period not in ("latest", "recent3", "all"):
        ranking_period = "all"
    ranking_issue_limit = {"latest": 1, "recent3": 3}.get(ranking_period)
    ranking_issue_ids = list(Issue.objects.order_by("-issue_number").values_list("issue_number", flat=True)[:ranking_issue_limit]) if ranking_issue_limit else None
    ranking_entries = Entry.objects.filter(issue_id__in=ranking_issue_ids) if ranking_issue_ids is not None else Entry.objects.all()

    status_counts = {value: 0 for value, _ in Entry.Status.choices}
    status_counts.update(dict(Entry.objects.values_list("status").annotate(total=Count("uuid"))))

    totals = Entry.objects.aggregate(entries=Count("uuid"), words=Sum("wordcount"))
    issue_rows = list(
        Issue.objects.annotate(
            total=Count("entries"),
            pending=Count("entries", filter=Q(entries__status=Entry.Status.PENDING)),
            waiting=Count("entries", filter=Q(entries__status=Entry.Status.CREATED)),
            reviewed=Count("entries", filter=Q(entries__status=Entry.Status.REVIEWED)),
            merged=Count("entries", filter=Q(entries__status=Entry.Status.SELECTED)),
            invalid=Count("entries", filter=Q(entries__status=Entry.Status.INVALID)),
            words=Sum("entries__wordcount"),
        ).order_by("issue_number")
    )
    timing_entries = Entry.objects.exclude(
        Q(versions__source=EntryFileVersion.Source.LEGACY)
        | Q(state_events__note__icontains="导入")
        | Q(state_events__note__startswith="由现有")
    ).distinct()
    timing_rows = list(timing_entries.values("created_at", "review_completed_at", "merged_at"))

    contributor_counts = {}
    for row in ranking_entries.values("submitter__username", "selector_name", "wordcount", "status"):
        name = row["submitter__username"] or row["selector_name"]
        if not name:
            continue
        item = contributor_counts.setdefault(name, {"username": name, "entries": 0, "words": 0, "merged": 0})
        item["entries"] += 1
        item["words"] += row["wordcount"] or 0
        item["merged"] += int(row["status"] == Entry.Status.SELECTED)

    collaborator_counts = {}

    def collaborator(name):
        if not name:
            return None
        return collaborator_counts.setdefault(name, {"username": name, "reviews": 0, "merges": 0, "comments": 0, "versions": 0})

    for row in EntryStateEvent.objects.filter(entry__in=ranking_entries, action__in=(EntryStateEvent.Action.REVIEW_COMPLETED, EntryStateEvent.Action.CLOSED_MERGED)).values("actor__username", "actor_name", "action"):
        item = collaborator(row["actor__username"] or row["actor_name"])
        if item:
            item["reviews" if row["action"] == EntryStateEvent.Action.REVIEW_COMPLETED else "merges"] += 1
    for row in EntryComment.objects.filter(entry__in=ranking_entries).values("author__username", "author_name").annotate(total=Count("id")):
        item = collaborator(row["author__username"] or row["author_name"])
        if item:
            item["comments"] += row["total"]
    for row in EntryFileVersion.objects.filter(entry__in=ranking_entries, source=EntryFileVersion.Source.REVIEW).values("uploader__username", "uploader_name").annotate(total=Count("id")):
        item = collaborator(row["uploader__username"] or row["uploader_name"])
        if item:
            item["versions"] += row["total"]

    user = request.user
    own_entries = Entry.objects.filter(Q(submitter=user) | Q(submitter__isnull=True, selector_name=user.username)).distinct()
    if user.is_staff or user.has_perm("current.review_entry"):
        review_issues = Issue.objects.all()
    else:
        review_issues = Issue.objects.filter(editors=user)
    if user.is_staff or user.has_perm("current.select_entry"):
        chief_issues = Issue.objects.all()
    else:
        chief_issues = Issue.objects.filter(Q(leader=user) | Q(responsible_editor=user))

    return Response({
        "generated_at": django_timezone.now().isoformat(),
        "ranking_period": ranking_period,
        "summary": {
            "issues": Issue.objects.count(),
            "published_issues": Issue.objects.filter(published=True).count(),
            "entries": totals["entries"] or 0,
            "words": totals["words"] or 0,
            "versions": EntryFileVersion.objects.count(),
            "comments": EntryComment.objects.count(),
        },
        "status_counts": status_counts,
        "workflow": {
            "average_review_hours": _average_hours(timing_rows, "created_at", "review_completed_at"),
            "average_decision_hours": _average_hours(timing_rows, "review_completed_at", "merged_at"),
            "returned_reviews": EntryStateEvent.objects.filter(action=EntryStateEvent.Action.REVIEW_RETURNED).count(),
            "reopened_entries": EntryStateEvent.objects.filter(action=EntryStateEvent.Action.REOPENED).count(),
        },
        "issues": [{
            "id": issue.issue_number,
            "published": issue.published,
            "total": issue.total,
            "pending": issue.pending,
            "waiting": issue.waiting,
            "reviewed": issue.reviewed,
            "merged": issue.merged,
            "invalid": issue.invalid,
            "words": issue.words or 0,
        } for issue in issue_rows],
        "pages": list(Entry.objects.values("page").annotate(total=Count("uuid"), merged=Count("uuid", filter=Q(status=Entry.Status.SELECTED)), words=Sum("wordcount")).order_by("page")),
        "contributors": sorted(contributor_counts.values(), key=lambda item: (-item["entries"], item["username"]))[:8],
        "collaborators": sorted(collaborator_counts.values(), key=lambda item: (-(item["reviews"] + item["merges"] + item["comments"] + item["versions"]), item["username"]))[:8],
        "personal": {
            "submitted": own_entries.count(),
            "merged": own_entries.filter(status=Entry.Status.SELECTED).count(),
            "reviewing": Entry.objects.filter(issue__in=review_issues, issue__published=False, status=Entry.Status.CREATED).distinct().count(),
            "awaiting_decision": Entry.objects.filter(issue__in=chief_issues, issue__published=False, status=Entry.Status.REVIEWED).distinct().count(),
        },
    })


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
        return Response(IssueSerializer(Issue.objects.all(), many=True, context={"request": request}).data)
    if not request.user.has_perm("current.create_issue"):
        return Response({"detail": "没有创建期刊的权限。"}, status=status.HTTP_403_FORBIDDEN)
    serializer = IssueCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    subjects = data["subject"]
    issue = Issue.objects.create(issue_number=data["id"], deadline=data["deadline"], subject2=subjects[0], subject3=subjects[1], subject4=subjects[2], leader=data.get("leader"), responsible_editor=data.get("responsible_editor"))
    issue.editors.set(data.get("editors", []))
    audit("issues.create", request.user.username, f"创建第 {issue.issue_number} 期")
    return Response(IssueSerializer(issue, context={"request": request}).data, status=status.HTTP_201_CREATED)


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
    return Response({"issue": IssueSerializer(issue, context={"request": request}).data, "entries": entries})


def _issue_pdf_response(issue, request):
    return Response(IssueSerializer(issue, context={"request": request}).data)


def _published_issue_response(issue):
    if issue.published:
        return Response({"detail": "期刊已经出版，请先撤回出版后再修改稿件。"}, status=status.HTTP_400_BAD_REQUEST)
    return None


def _lock_entry_issue(entry):
    entry.issue = Issue.objects.select_for_update().get(pk=entry.issue_id)
    return entry


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@transaction.atomic
def upload_issue_pdf(request, issue_number):
    try:
        issue = Issue.objects.select_for_update().get(issue_number=issue_number)
    except Issue.DoesNotExist:
        return Response({"detail": "期刊不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not can_manage_issue_pdf(request.user, issue):
        return Response({"detail": "只有主编级用户可以管理期刊 PDF。"}, status=status.HTTP_403_FORBIDDEN)
    if issue.published:
        return Response({"detail": "请先撤回出版后再替换 PDF。"}, status=status.HTTP_400_BAD_REQUEST)
    pdf = request.FILES.get("pdf")
    if not pdf:
        return Response({"detail": "请选择 PDF 文件。"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_pdf_upload(pdf)
    except serializers.ValidationError as exc:
        return Response({"detail": exc.detail[0]}, status=status.HTTP_400_BAD_REQUEST)
    issue.pdf = pdf
    issue.save(update_fields=["pdf"])
    audit("issues.pdf.upload", request.user.username, f"上传第 {issue.issue_number} 期 PDF")
    return _issue_pdf_response(issue, request)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@transaction.atomic
def publish_issue(request, issue_number):
    try:
        issue = Issue.objects.select_for_update().get(issue_number=issue_number)
    except Issue.DoesNotExist:
        return Response({"detail": "期刊不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not can_manage_issue_pdf(request.user, issue):
        return Response({"detail": "只有主编级用户可以发布期刊。"}, status=status.HTTP_403_FORBIDDEN)
    if issue.published:
        return Response({"detail": "期刊已经发布。"}, status=status.HTTP_400_BAD_REQUEST)
    if request.FILES.get("pdf"):
        pdf = request.FILES["pdf"]
        try:
            validate_pdf_upload(pdf)
        except serializers.ValidationError as exc:
            return Response({"detail": exc.detail[0]}, status=status.HTTP_400_BAD_REQUEST)
        issue.pdf = pdf
    if not issue.pdf:
        return Response({"detail": "请先上传 PDF 文件再发布。"}, status=status.HTTP_400_BAD_REQUEST)
    issue.published = True
    issue.save(update_fields=["pdf", "published"])
    audit("issues.publish", request.user.username, f"发布第 {issue.issue_number} 期")
    return _issue_pdf_response(issue, request)


@api_view(["POST"])
@transaction.atomic
def unpublish_issue(request, issue_number):
    try:
        issue = Issue.objects.select_for_update().get(issue_number=issue_number)
    except Issue.DoesNotExist:
        return Response({"detail": "期刊不存在。"}, status=status.HTTP_404_NOT_FOUND)
    if not can_manage_issue_pdf(request.user, issue):
        return Response({"detail": "只有主编级用户可以撤回出版。"}, status=status.HTTP_403_FORBIDDEN)
    if not issue.published:
        return Response({"detail": "期刊当前未出版。"}, status=status.HTTP_400_BAD_REQUEST)
    issue.published = False
    issue.save(update_fields=["published"])
    audit("issues.unpublish", request.user.username, f"撤回第 {issue.issue_number} 期出版")
    return _issue_pdf_response(issue, request)


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
@transaction.atomic
def entries(request, issue_number):
    if not request.user.has_perm("current.create_entry"):
        return Response({"detail": "没有创建投稿的权限。"}, status=status.HTTP_403_FORBIDDEN)
    try:
        issue = Issue.objects.select_for_update().get(issue_number=issue_number)
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
@transaction.atomic
def upload_entry_version(request, entry_uuid):
    try:
        entry = Entry.objects.select_for_update().select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    _lock_entry_issue(entry)
    if not is_entry_reviewer(request.user, entry):
        return Response({"detail": "没有上传审核版本的权限。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status != Entry.Status.CREATED or entry.issue.published:
        return Response({"detail": "稿件当前不能再上传审核版本。"}, status=status.HTTP_400_BAD_REQUEST)
    serializer = EntryVersionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

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
@transaction.atomic
def add_entry_comment(request, entry_uuid):
    try:
        entry = Entry.objects.select_for_update().select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    _lock_entry_issue(entry)
    if response := _published_issue_response(entry.issue):
        return response
    if not can_comment_on_entry(request.user, entry) or entry.status in (Entry.Status.SELECTED, Entry.Status.INVALID):
        return Response({"detail": "没有在此稿件留言的权限。"}, status=status.HTTP_403_FORBIDDEN)
    serializer = EntryCommentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    comment = EntryComment.objects.create(entry=entry, author=request.user, author_name=request.user.username, body=serializer.validated_data["body"])
    audit("entries.comment.create", request.user.username, f"在投稿 {entry.uuid} 留言")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@transaction.atomic
def complete_entry_review(request, entry_uuid):
    try:
        entry = Entry.objects.select_for_update().select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    _lock_entry_issue(entry)
    if response := _published_issue_response(entry.issue):
        return response
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


@api_view(["POST"])
@transaction.atomic
def return_entry_to_review(request, entry_uuid):
    try:
        entry = Entry.objects.select_for_update().select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    _lock_entry_issue(entry)
    if response := _published_issue_response(entry.issue):
        return response
    if not is_entry_chief(request.user, entry):
        return Response({"detail": "只有主编级用户可以退回重新审核。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status != Entry.Status.REVIEWED:
        return Response({"detail": "只有审核完成且尚未合并的稿件可以退回重新审核。"}, status=status.HTTP_400_BAD_REQUEST)
    serializer = EntryReopenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    entry.status = Entry.Status.CREATED
    entry.reviewer_name = ""
    entry.review_completed_by = None
    entry.review_completed_at = None
    entry.save(update_fields=["status", "reviewer_name", "review_completed_by", "review_completed_at", "updated_at"])
    EntryStateEvent.objects.create(
        entry=entry,
        action=EntryStateEvent.Action.REVIEW_RETURNED,
        actor=request.user,
        actor_name=request.user.username,
        from_status=Entry.Status.REVIEWED,
        to_status=Entry.Status.CREATED,
        note=serializer.validated_data.get("note", ""),
    )
    audit("entries.review.return", request.user.username, f"退回投稿 {entry.uuid} 重新审核")
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
@transaction.atomic
def close_entry(request, entry_uuid):
    try:
        entry = Entry.objects.select_for_update().select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    _lock_entry_issue(entry)
    if response := _published_issue_response(entry.issue):
        return response
    if not is_entry_chief(request.user, entry):
        return Response({"detail": "只有主编级用户可以关闭稿件。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status not in (Entry.Status.CREATED, Entry.Status.REVIEWED):
        return Response({"detail": "稿件当前不能关闭。"}, status=status.HTTP_400_BAD_REQUEST)
    serializer = EntryCloseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    disposition = serializer.validated_data["disposition"]
    if disposition == "merged" and entry.status != Entry.Status.REVIEWED:
        return Response({"detail": "只有已完成审核的稿件可以关闭并合并。"}, status=status.HTTP_400_BAD_REQUEST)
    _close_entry(entry, request.user, disposition, serializer.validated_data.get("note", ""))
    audit(f"entries.close.{disposition}", request.user.username, f"关闭投稿 {entry.uuid}")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data)


@api_view(["POST"])
@transaction.atomic
def merge_entry(request, entry_uuid):
    try:
        entry = Entry.objects.select_for_update().select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    _lock_entry_issue(entry)
    if response := _published_issue_response(entry.issue):
        return response
    if not is_entry_chief(request.user, entry):
        return Response({"detail": "只有主编级用户可以合并稿件。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status != Entry.Status.REVIEWED:
        return Response({"detail": "只有已完成审核的稿件可以关闭并合并。"}, status=status.HTTP_400_BAD_REQUEST)
    _close_entry(entry, request.user, "merged")
    audit("entries.close.merged", request.user.username, f"关闭并合并投稿 {entry.uuid}")
    return Response(EntryReviewSerializer(entry, context={"request": request}).data)


@api_view(["POST"])
@transaction.atomic
def reopen_entry(request, entry_uuid):
    try:
        entry = Entry.objects.select_for_update().select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    _lock_entry_issue(entry)
    if response := _published_issue_response(entry.issue):
        return response
    if not is_entry_chief(request.user, entry):
        return Response({"detail": "只有主编级用户可以重新打开稿件。"}, status=status.HTTP_403_FORBIDDEN)
    if entry.status not in (Entry.Status.SELECTED, Entry.Status.INVALID):
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
@transaction.atomic
def remove_entry(request, entry_uuid):
    if not request.user.has_perm("current.remove_entry"):
        return Response({"detail": "没有删除投稿的权限。"}, status=status.HTTP_403_FORBIDDEN)
    try:
        entry = Entry.objects.select_for_update().select_related("issue").get(uuid=entry_uuid)
    except Entry.DoesNotExist:
        return Response({"detail": "投稿不存在。"}, status=status.HTTP_404_NOT_FOUND)
    _lock_entry_issue(entry)
    if response := _published_issue_response(entry.issue):
        return response
    entry.delete()
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
