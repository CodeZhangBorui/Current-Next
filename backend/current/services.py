from django.utils import timezone

from .models import AuditLog, SiteConfig


def audit(scope, executor, message):
    AuditLog.objects.create(timestamp=timezone.now(), scope=scope, executor=executor or "", message=message)


def get_config(key, default=""):
    item = SiteConfig.objects.filter(key=key).first()
    return item.value if item else default


def set_config(key, value, value_type="str"):
    SiteConfig.objects.update_or_create(key=key, defaults={"value": value, "value_type": value_type})
