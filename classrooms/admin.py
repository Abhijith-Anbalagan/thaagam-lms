from django.contrib import admin
from .models import Classroom, CourseContent


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'teacher', 'school', 'student_count', 'created_at']
    list_filter   = ['school']
    search_fields = ['name', 'code', 'teacher__username']
    readonly_fields = ['code']


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'content_type', 'classroom', 'unit', 'created_at']
    list_filter  = ['content_type']
