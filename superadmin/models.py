from django.db import models


class School(models.Model):
    name       = models.CharField(max_length=200)
    address    = models.TextField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_students(self):
        return self.users.filter(role='student').count()

    @property
    def total_teachers(self):
        return self.users.filter(role='teacher').count()

    @property
    def total_classrooms(self):
        from classrooms.models import Classroom
        return Classroom.objects.filter(school=self).count()


class GlobalCourse(models.Model):
    """Courses created by Super Admin and assigned to schools."""
    STATUS = [('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')]

    title      = models.CharField(max_length=200)
    content    = models.TextField(blank=True)
    school     = models.ForeignKey(School, null=True, blank=True, on_delete=models.SET_NULL)
    status     = models.CharField(max_length=10, choices=STATUS, default='draft')
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='global_courses'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
