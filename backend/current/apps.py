from django.apps import AppConfig


class CurrentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "current"
    verbose_name = "Current 系统"

    def ready(self):
        from . import signals  # noqa: F401
