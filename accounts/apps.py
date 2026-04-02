from django.apps import AppConfig
from django.utils import timezone


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals  # noqa
        self.initialize_teacher_presence_cache()

    def initialize_teacher_presence_cache(self):
        """Initialize presence cache for teachers on app startup."""
        from django.core.cache import cache
        from django.contrib.sessions.models import Session
        from django.contrib.auth import get_user_model
        from django.db.utils import OperationalError, ProgrammingError

        try:
            User = get_user_model()
            sessions = Session.objects.filter(expire_date__gt=timezone.now())

            teacher_ids = set()
            for session in sessions:
                try:
                    session_data = session.get_decoded()
                    user_id = session_data.get('_auth_user_id')
                    if user_id:
                        try:
                            user = User.objects.get(pk=user_id, role='teacher')
                            teacher_ids.add(user.pk)
                        except User.DoesNotExist:
                            pass
                except:
                    continue

            for teacher_id in teacher_ids:
                cache.set(f'user_online_{teacher_id}', True, timeout=None)

        except (OperationalError, ProgrammingError):
            # Database tables don't exist yet (before first migration)
            return