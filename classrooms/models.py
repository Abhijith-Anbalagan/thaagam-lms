import random
import string
from django.db import models


def _generate_code():
    """Generate a unique 6-character alphanumeric classroom code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if not Classroom.objects.filter(code=code).exists():
            return code


class Classroom(models.Model):
    name       = models.CharField(max_length=200)
    code       = models.CharField(max_length=6, unique=True, blank=True)
    teacher    = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='classrooms',
        limit_choices_to={'role': 'teacher'},
    )
    school     = models.ForeignKey(
        'superadmin.School',
        on_delete=models.CASCADE,
        related_name='classrooms',
    )
    students   = models.ManyToManyField(
        'accounts.User',
        blank=True,
        related_name='joined_classrooms',
        limit_choices_to={'role': 'student'},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering  = ['-created_at']
        db_table  = 'classrooms_classroom'   # ← locked — do NOT change

    def __str__(self):
        return f'{self.name} [{self.code}]'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _generate_code()
        super().save(*args, **kwargs)

    @property
    def student_count(self):
        return self.students.count()

    @property
    def pending_submission_count(self):
        """How many student×assignment pairs have no submission yet."""
        from assignments.models import Submission
        total_expected = self.assignments.count() * self.student_count
        submitted      = Submission.objects.filter(
            assignment__classroom=self
        ).count()
        return max(0, total_expected - submitted)


class CourseContent(models.Model):
    CONTENT_TYPES = [
        ('video', 'Video'),
        ('pdf',   'PDF'),
        ('note',  'Note'),
    ]

    classroom    = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name='course_contents'
    )
    title        = models.CharField(max_length=200)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    file         = models.FileField(upload_to='course_files/', blank=True, null=True)
    video_url    = models.URLField(blank=True)
    unit         = models.CharField(
        max_length=100, blank=True,
        help_text='Chapter / unit label for grouping, e.g. "Unit 1 — Algebra"'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering  = ['unit', 'created_at']
        db_table  = 'classrooms_coursecontent'   # ← locked — do NOT change

    def __str__(self):
        return f'[{self.get_content_type_display()}] {self.title}'
