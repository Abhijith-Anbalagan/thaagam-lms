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


# superadmin/models.py  — GlobalCourse model

class GlobalCourse(models.Model):
    """Courses created by Super Admin and assigned to schools."""
    STATUS = [('draft', 'Draft'), ('published', 'Published')]
    LEVEL  = [('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')]
    LANGUAGE_CHOICES = [
        ('english', 'English'), ('tamil', 'Tamil'), ('hindi', 'Hindi'),
        ('telugu', 'Telugu'), ('kannada', 'Kannada'),
    ]

    title         = models.CharField(max_length=200)
    description   = models.TextField(blank=True)
    cover_image   = models.ImageField(upload_to='course_covers/', blank=True, null=True)  # NEW
    language      = models.CharField(max_length=30, choices=LANGUAGE_CHOICES, default='english')  # NEW
    total_hours   = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # NEW
    is_free       = models.BooleanField(default=True)   # NEW
    has_certificate = models.BooleanField(default=True) # NEW
    summary       = models.TextField(blank=True)        # NEW
    schools       = models.ManyToManyField(School, blank=True, related_name='global_courses')
    status        = models.CharField(max_length=10, choices=STATUS, default='draft')
    created_by    = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='global_courses'
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'superadmin_globalcourse'

    def __str__(self):
        return self.title


class GlobalConceptVideo(models.Model):
    """Multiple videos per concept."""
    concept    = models.ForeignKey('GlobalConcept', on_delete=models.CASCADE, related_name='videos')
    title      = models.CharField(max_length=200, blank=True)
    file       = models.FileField(upload_to='global_concepts/videos/', blank=True, null=True)
    video_url  = models.URLField(blank=True)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'superadmin_globalconceptvideo'
        ordering = ['order']

    def __str__(self):
        return f'{self.concept.header} — video {self.order}'


class GlobalConcept(models.Model):
    """A concept/chapter inside a GlobalCourse."""
    LEVEL = [('beginner','Beginner'),('intermediate','Intermediate'),('advanced','Advanced')]

    course      = models.ForeignKey(GlobalCourse, on_delete=models.CASCADE, related_name='concepts')
    header      = models.CharField(max_length=200)
    h3_course   = models.CharField(max_length=200, blank=True)
    level       = models.CharField(max_length=20, choices=LEVEL, default='beginner') 
    pdf         = models.FileField(upload_to='global_concepts/pdfs/', blank=True, null=True)
    quiz        = models.TextField(blank=True)
    assignment  = models.TextField(blank=True)
    order       = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'superadmin_globalconcept'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.course.title} — {self.header}'
