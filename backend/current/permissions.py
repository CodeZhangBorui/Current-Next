from rest_framework.permissions import BasePermission


class IsCurrentStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


def is_entry_reviewer(user, entry):
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.is_staff
        or user.has_perm("current.review_entry")
        or entry.issue.editors.filter(pk=user.pk).exists()
    )


def is_entry_chief(user, entry):
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.is_staff
        or user.has_perm("current.select_entry")
        or entry.issue.leader_id == user.pk
        or entry.issue.responsible_editor_id == user.pk
    )


def can_manage_issue_pdf(user, issue):
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.is_staff
        or user.has_perm("current.publish_issue")
        or issue.leader_id == user.pk
        or issue.responsible_editor_id == user.pk
    )


def can_comment_on_entry(user, entry):
    return bool(
        user
        and user.is_authenticated
        and (entry.submitter_id == user.pk or is_entry_reviewer(user, entry) or is_entry_chief(user, entry))
    )
