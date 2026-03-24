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
    STATUS = [('draft', 'Draft'), ('published', 'Published')]

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    schools     = models.ManyToManyField(School, blank=True, related_name='global_courses')
    status      = models.CharField(max_length=10, choices=STATUS, default='draft')
    created_by  = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='global_courses'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'superadmin_globalcourse'

    def __str__(self):
        return self.title


class GlobalConcept(models.Model):
    """A concept/chapter inside a GlobalCourse."""
    course      = models.ForeignKey(GlobalCourse, on_delete=models.CASCADE, related_name='concepts')
    header      = models.CharField(max_length=200)
    h3_course   = models.CharField(max_length=200, blank=True)
    videos      = models.FileField(upload_to='global_concepts/videos/', blank=True, null=True)
    pdf         = models.FileField(upload_to='global_concepts/pdfs/',   blank=True, null=True)
    quiz        = models.TextField(blank=True, help_text='Quiz questions (text/JSON)')
    assignment  = models.TextField(blank=True, help_text='Assignment instructions')
    order       = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'superadmin_globalconcept'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.course.title} — {self.header}'
