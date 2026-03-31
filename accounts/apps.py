from django.apps import AppConfig
from django.utils import timezone
from django.db.utils import OperationalError, ProgrammingError
import sys


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals  # noqa

        # 🚫 Skip during migrations & makemigrations
        if 'makemigrations' in sys.argv or 'migrate' in sys.argv:
            return

        try:
            self.initialize_teacher_presence_cache()
        except (OperationalError, ProgrammingError):
            # DB not ready yet
            return

    def initialize_teacher_presence_cache(self):
        """Initialize presence cache for teachers on app startup."""
        from django.core.cache import cache
        from django.contrib.sessions.models import Session
        from django.contrib.auth import get_user_model

        User = get_user_model()

        sessions = Session.objects.filter(expire_date__gt=timezone.now())

        teacher_ids = set()
        for session in sessions:
            try:
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')

                if user_id:
                    user = User.objects.filter(pk=user_id, role='teacher').first()
                    if user:
                        teacher_ids.add(user.pk)

            except Exception:
                continue

        for teacher_id in teacher_ids:
            cache.set(f'user_online_{teacher_id}', True, timeout=None)