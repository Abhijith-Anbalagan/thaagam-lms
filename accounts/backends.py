from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User

class IdentificationBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL using either email or student_id.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        try:
            # Try to find a user by email OR student_id
            user = User.objects.get(Q(email__iexact=username) | Q(student_id=username))
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the vulnerability to timing attacks.
            User().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
