from django.db import models


class Announcement(models.Model):
    TARGET = [('all', 'Everyone'), ('teachers', 'Teachers Only'), ('students', 'Students Only')]

    posted_by  = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='announcements')
    school     = models.ForeignKey('superadmin.School', on_delete=models.CASCADE, related_name='announcements')
    classroom  = models.ForeignKey(
        'classrooms.Classroom', on_delete=models.CASCADE,
        related_name='announcements', null=True, blank=True
    )
    title      = models.CharField(max_length=200)
    body       = models.TextField()
    meet_link  = models.URLField(blank=True)
    target     = models.CharField(max_length=10, choices=TARGET, default='all')
    is_pinned  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title
