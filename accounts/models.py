import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    ROLES = [
        ('super_admin', 'Super Admin'),
        ('school_admin', 'School Admin'),
        ('management', 'Management'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('public', 'Public'),
    ]

    role   = models.CharField(max_length=20, choices=ROLES, default='public')
    school = models.ForeignKey(
        'superadmin.School', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='users'
    )
    phone  = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f'{self.username} ({self.role})'

    @property
    def role_color(self):
        return {
            'super_admin':  '#993c1d',
            'school_admin': '#534ab7',
            'management':   '#2d3561',
            'teacher':      '#0f6e56',
            'student':      '#3b6d11',
            'public':       '#9e9c95',
        }.get(self.role, '#9e9c95')

    def get_dashboard_url(self):
        return {
            'super_admin':  '/superadmin/dashboard/',
            'school_admin': '/school-admin/dashboard/',
            'management':   '/management/dashboard/',
            'teacher':      '/teacher/dashboard/',
            'student':      '/student/dashboard/',
            'public':       '/public-dashboard/',
        }.get(self.role, '/login/')


def _default_expiry():
    return timezone.now() + timedelta(hours=48)


class Invitation(models.Model):
    email      = models.EmailField()
    role       = models.CharField(max_length=20)
    school     = models.ForeignKey(
        'superadmin.School', on_delete=models.CASCADE, related_name='invitations'
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_invites'
    )
    token      = models.UUIDField(default=uuid.uuid4, unique=True)
    accepted   = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=_default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Invite → {self.email} ({self.role})'

    @property
    def is_valid(self):
        return not self.accepted and timezone.now() < self.expires_at
