from datetime import timedelta

from django.db import models
from django.utils import timezone


class School(models.Model):
    name       = models.CharField(max_length=200)
    address    = models.TextField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.deadline_at is None:
            self.deadline_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

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
    STATUS = [('draft', 'Unpublished'), ('published', 'Published')]
    LEVEL  = [('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')]
    LANGUAGE_CHOICES = [
        ('english', 'English'), ('tamil', 'Tamil'), ('hindi', 'Hindi'),
        ('telugu', 'Telugu'), ('kannada', 'Kannada'),
    ]

    title           = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    cover_image     = models.ImageField(upload_to='course_covers/', blank=True, null=True)
    language        = models.CharField(max_length=30, choices=LANGUAGE_CHOICES, default='english')
    total_hours     = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    is_free         = models.BooleanField(default=True)
    has_certificate = models.BooleanField(default=True)
    summary         = models.TextField(blank=True)
    schools         = models.ManyToManyField(School, blank=True, related_name='global_courses')
    status          = models.CharField(max_length=10, choices=STATUS, default='draft')
    created_by      = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='global_courses'
    )
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'superadmin_globalcourse'

    def __str__(self):
        return self.title


class GlobalConceptVideo(models.Model):
    concept   = models.ForeignKey('GlobalConcept', on_delete=models.CASCADE, related_name='videos')
    title     = models.CharField(max_length=200, blank=True)
    file      = models.FileField(upload_to='global_concepts/videos/', blank=True, null=True)
    video_url = models.URLField(blank=True)
    order     = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'superadmin_globalconceptvideo'
        ordering = ['order']

    def __str__(self):
        return f'{self.concept.header} — video {self.order}'


class GlobalConcept(models.Model):
    LEVEL = [('beginner','Beginner'),('intermediate','Intermediate'),('advanced','Advanced')]

    course     = models.ForeignKey(GlobalCourse, on_delete=models.CASCADE, related_name='concepts')
    header     = models.CharField(max_length=200)
    h3_course  = models.CharField(max_length=200, blank=True)
    level      = models.CharField(max_length=20, choices=LEVEL, default='beginner')
    pdf        = models.FileField(upload_to='global_concepts/pdfs/', blank=True, null=True)
    quiz       = models.TextField(blank=True)
    assignment = models.TextField(blank=True)
    order      = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'superadmin_globalconcept'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.course.title} — {self.header}'


class CourseEnrollment(models.Model):
    """Tracks which users (teacher/student) enrolled in which GlobalCourse."""
    user        = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='enrollments'
    )
    course      = models.ForeignKey(
        GlobalCourse, on_delete=models.CASCADE, related_name='enrollments'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'superadmin_courseenrollment'
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.user.username} → {self.course.title}'
    
    def save(self, *args, **kwargs):
        if self.deadline_at is None:
            self.deadline_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

# class ClassroomCourseAssignment(models.Model):
#     classroom = models.ForeignKey('classrooms.Classroom', on_delete=models.CASCADE, related_name='course_assignments')
#     course = models.ForeignKey('superadmin.GlobalCourse', on_delete=models.CASCADE, related_name='classroom_assignments')
#     assigned_at = models.DateTimeField(auto_now_add=True)
#     class Meta:
#         unique_together = ('classroom', 'course')

class ClassroomCourseAssignment(models.Model):
    """Tracks which GlobalCourses are assigned to which Classroom."""
    classroom = models.ForeignKey(
        'classrooms.Classroom',
        on_delete=models.CASCADE,
        related_name='course_assignments',
    )
    course = models.ForeignKey(
        'superadmin.GlobalCourse',
        on_delete=models.CASCADE,
        related_name='classroom_assignments',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('classroom', 'course')
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.classroom.name} ← {self.course.title}"
