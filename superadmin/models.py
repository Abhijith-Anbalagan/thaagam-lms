import re
from datetime import timedelta

from django.db import models
from django.utils import timezone


# ─── shared URL normaliser ────────────────────────────────────────────────────
_YT_RE    = re.compile(
    r'(?:https?://)?(?:www\.)?'
    r'(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|v/)|youtu\.be/)'
    r'([A-Za-z0-9_-]{11})'
)
_VIMEO_RE = re.compile(r'vimeo\.com/(?:video/)?(\d+)')
_IFRAME_SRC_RE = re.compile(r'src=["\']([^"\']+)["\']')


def parse_to_embed_url(raw: str) -> str:
    """
    Accept any of:
      • YouTube watch URL   https://www.youtube.com/watch?v=ID
      • YouTube short URL   https://youtu.be/ID
      • YouTube Shorts      https://www.youtube.com/shorts/ID
      • YouTube <iframe>    <iframe src="https://www.youtube.com/embed/ID?...">
      • Vimeo URL / iframe
    Returns a clean embed URL ready for <iframe src="...">.
    Falls back to the original string if nothing matches.
    """
    if not raw:
        return raw
    
    # decode HTML entities that browsers / copy-paste may introduce
    raw = (raw.replace('&amp;', '&').replace('&quot;', '"')
              .replace('&lt;', '<').replace('&gt;', '>'))

    # if someone pasted a full <iframe> snippet, pull out the src
    m = _IFRAME_SRC_RE.search(raw)
    if m:
        raw = m.group(1).replace('&amp;', '&')

    # YouTube → embed
    yt = _YT_RE.search(raw)
    if yt:
        return f'https://www.youtube.com/embed/{yt.group(1)}'

    # Vimeo → embed
    vimeo = _VIMEO_RE.search(raw)
    if vimeo:
        return f'https://player.vimeo.com/video/{vimeo.group(1)}'

    # already an embed URL or unknown — return as-is
    return raw


class School(models.Model):
    name       = models.CharField(max_length=200)
    domain     = models.CharField(max_length=100, blank=True, help_text="e.g. thaagam.org")
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

    @property
    def computed_hours(self):
        """Sum of all video duration_seconds across all concepts, converted to hours."""
        from django.db.models import Sum
        total = GlobalConceptVideo.objects.filter(
            concept__course=self
        ).aggregate(total=Sum('duration_seconds'))['total'] or 0
        return round(total / 3600, 1)

    @property
    def total_duration_seconds(self):
        """Raw total seconds of all uploaded videos in this course."""
        from django.db.models import Sum
        return GlobalConceptVideo.objects.filter(
            concept__course=self
        ).aggregate(total=Sum('duration_seconds'))['total'] or 0

    @property
    def duration_display(self):
        """Human-readable duration: e.g. '2h 15m 30s', '45m 10s', '30s'"""
        secs = self.total_duration_seconds
        if not secs:
            return '0m'
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        if h > 0:
            return f'{h}h {m}m {s}s' if s else (f'{h}h {m}m' if m else f'{h}h')
        if m > 0:
            return f'{m}m {s}s' if s else f'{m}m'
        return f'{s}s'

    def sync_total_hours(self):
        """Recalculate and save total_hours from actual video durations."""
        self.total_hours = self.computed_hours
        self.save(update_fields=['total_hours'])

        
class GlobalConceptVideo(models.Model):
    concept          = models.ForeignKey('GlobalConcept', on_delete=models.CASCADE, related_name='videos')
    title            = models.CharField(max_length=200, blank=True)
    file             = models.FileField(upload_to='global_concepts/videos/', blank=True, null=True)
    video_url        = models.URLField(max_length=500, blank=True)
    cover_image      = models.ImageField(upload_to='global_concepts/video_covers/', blank=True, null=True)
    order            = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)  # stored when video is uploaded

    class Meta:
        db_table = 'superadmin_globalconceptvideo'
        ordering = ['order']

    def save(self, *args, **kwargs):
        # Auto-convert any YouTube/Vimeo input to a clean embed URL before saving
        if self.video_url:
            self.video_url = parse_to_embed_url(self.video_url)
        super().save(*args, **kwargs)

    @property
    def is_youtube(self):
        return 'youtube.com/embed/' in (self.video_url or '')

    @property
    def is_vimeo(self):
        return 'player.vimeo.com' in (self.video_url or '')

    @property
    def is_external(self):
        return bool(self.video_url) and not self.file

    def __str__(self):
        return f'{self.concept.header} — video {self.order}'


class GlobalConcept(models.Model):
    LEVEL = [('beginner','Beginner'),('intermediate','Intermediate'),('advanced','Advanced')]

    course     = models.ForeignKey(GlobalCourse, on_delete=models.CASCADE, related_name='concepts')
    header     = models.CharField(max_length=200)
    h3_course  = models.CharField(max_length=200, blank=True)
    level      = models.CharField(max_length=20, choices=LEVEL, default='beginner')
    pdf        = models.FileField(upload_to='global_concepts/pdfs/', blank=True, null=True)
    pdf_url    = models.URLField(blank=True, max_length=500)
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
    is_completed = models.BooleanField(default=False)

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


class ConceptProgress(models.Model):
    """Tracks which concepts a student has marked as completed."""
    student  = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='concept_progress'
    )
    concept  = models.ForeignKey(
        GlobalConcept, on_delete=models.CASCADE, related_name='progress_records'
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'superadmin_conceptprogress'
        unique_together = ('student', 'concept')

    def __str__(self):
        return f'{self.student.username} ✓ {self.concept.header}'
