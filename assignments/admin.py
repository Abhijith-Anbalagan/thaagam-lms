from django.contrib import admin
from .models import Assignment, Submission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display  = ['title', 'classroom', 'due_date', 'max_score', 'is_overdue']
    list_filter   = ['classroom__school']
    search_fields = ['title']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display  = ['student', 'assignment', 'submitted_at', 'score', 'is_late']
    list_filter   = ['assignment__classroom']
    search_fields = ['student__username']
