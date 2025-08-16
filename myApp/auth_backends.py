# myApp/auth_backends.py
import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

class EmailOrUsernameCIBackend(ModelBackend):
    """
    Authenticate with email OR username (case-insensitive).
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        ident = (username or "").strip()

        # Try email (case-insensitive), then username (case-insensitive)
        user = (User.objects.filter(email__iexact=ident).first()
                or User.objects.filter(username__iexact=ident).first())

        if not user:
            logger.debug("Auth fail: no user for ident=%r", ident)
            return None
        if not user.check_password(password):
            logger.debug("Auth fail: bad password for user_id=%s", user.id)
            return None
        if not self.user_can_authenticate(user):
            logger.debug("Auth fail: user cannot authenticate (inactive?) user_id=%s", user.id)
            return None

        logger.debug("Auth OK for user_id=%s via ident=%r", user.id, ident)
        return user
