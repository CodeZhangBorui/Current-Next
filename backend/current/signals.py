from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.utils.translation import override

from .models import User


ACTION_NAMES = {
    "add": "添加",
    "change": "修改",
    "delete": "删除",
    "view": "查看",
}


def grant_default_permission(user):
    if Permission.objects.filter(name__startswith="Can ").exists():
        localize_permission_names()
    permission = Permission.objects.filter(content_type__app_label="current", codename="create_entry").first()
    if permission:
        user.user_permissions.add(permission)


def localize_permission_names():
    with override(settings.LANGUAGE_CODE):
        for permission in Permission.objects.select_related("content_type"):
            try:
                model = apps.get_model(permission.content_type.app_label, permission.content_type.model)
            except LookupError:
                continue
            custom_names = dict(model._meta.permissions)
            if permission.codename in custom_names:
                name = custom_names[permission.codename]
            else:
                action = permission.codename.split("_", 1)[0]
                if action not in ACTION_NAMES:
                    continue
                name = f"{ACTION_NAMES[action]}{model._meta.verbose_name}"
            if permission.name != name:
                Permission.objects.filter(pk=permission.pk).update(name=name)


@receiver(post_save, sender=User)
def grant_default_entry_permission(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        grant_default_permission(instance)


@receiver(post_migrate)
def configure_permissions(sender, **kwargs):
    if sender.label != "current":
        return
    localize_permission_names()
    permission = Permission.objects.filter(content_type__app_label="current", codename="create_entry").first()
    if permission:
        through = User.user_permissions.through
        through.objects.bulk_create(
            [through(user_id=user_id, permission_id=permission.pk) for user_id in User.objects.values_list("pk", flat=True)],
            ignore_conflicts=True,
        )
