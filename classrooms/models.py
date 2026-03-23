import random
import string
from django.db import models


def _generate_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if not Classroom.objects.filter(code=code).exists():
            return code


class Classroom(models.Model):
    name       = models.CharField(max_length=200)
    code       = models.CharField(max_length=6, unique=True, blank=True)
    teacher    = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='classrooms'
    )
    school     = models.ForeignKey(
        'superadmin.School', on_delete=models.CASCADE, related_name='classrooms'
    )
    students   = models.ManyToManyField(
        'accounts.User', blank=True, related_name='joined_classrooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} [{self.code}]'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _generate_code()
        super().save(*args, **kwargs)

    @property
    def student_count(self):
        return self.students.count()


class CourseContent(models.Model):
    TYPES = [('video', 'Video'), ('pdf', 'PDF'), ('note', 'Note')]

    classroom    = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='course_contents')
    title        = models.CharField(max_length=200)
    content_type = models.CharField(max_length=10, choices=TYPES)
    file         = models.FileField(upload_to='course_files/', blank=True, null=True)
    video_url    = models.URLField(blank=True)
    unit         = models.CharField(max_length=100, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['unit', 'created_at']

    def __str__(self):
        return self.title
