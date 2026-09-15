from django.utils import timezone

from .models import AuditLog, SiteConfig


def audit(scope, executor, message):
    AuditLog.objects.create(timestamp=timezone.now(), scope=scope, executor=executor or "", message=message)


def get_config(key, default=""):
    item = SiteConfig.objects.filter(key=key).first()
    return item.value if item else default
