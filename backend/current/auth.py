import hashlib

from django.contrib.auth import get_user_model


class LegacyPasswordBackend:
    """Accept old SHA-256 passwords once, then transparently upgrade them."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None:
            return None
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
        except user_model.DoesNotExist:
            return None
        if not user.is_active:
            return None
        legacy_hash = user.legacy_password_hash
        if not legacy_hash or not hashlib.sha256(password.encode("utf-8")).hexdigest() == legacy_hash:
            return None
        user.set_password(password)
        user.legacy_password_hash = ""
        user.save(update_fields=["password", "legacy_password_hash"])
        return user

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
        return user if user.is_active else None
