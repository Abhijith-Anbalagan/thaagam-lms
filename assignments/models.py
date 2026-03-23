from django.db import models
from django.utils import timezone


class Assignment(models.Model):
    classroom   = models.ForeignKey(
        'classrooms.Classroom', on_delete=models.CASCADE, related_name='assignments'
    )
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date    = models.DateTimeField()
    max_score   = models.PositiveIntegerField(default=20)
    file        = models.FileField(upload_to='assignment_files/', blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — {self.classroom.name}'

    @property
    def is_overdue(self):
        return timezone.now() > self.due_date


class Submission(models.Model):
    assignment   = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student      = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='submissions')
    file         = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    score        = models.PositiveIntegerField(null=True, blank=True)
    feedback     = models.TextField(blank=True)

    class Meta:
        unique_together = ['assignment', 'student']

    def __str__(self):
        return f'{self.student.username} → {self.assignment.title}'

    @property
    def is_late(self):
        return self.submitted_at > self.assignment.due_date

    @property
    def percentage(self):
        if self.score is not None and self.assignment.max_score:
            return round((self.score / self.assignment.max_score) * 100, 1)
        return None

    @property
    def letter_grade(self):
        p = self.percentage
        if p is None: return '—'
        if p >= 90:   return 'A'
        if p >= 80:   return 'B'
        if p >= 70:   return 'C'
        if p >= 60:   return 'D'
        return 'F'
