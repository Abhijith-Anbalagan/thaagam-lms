from django.contrib import admin
from .models import Announcement
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'posted_by', 'school', 'classroom', 'is_pinned', 'created_at']
