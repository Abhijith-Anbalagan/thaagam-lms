from django.contrib import admin
from .models import Classroom, CourseContent

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'teacher', 'school', 'student_count']

@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'content_type', 'classroom', 'unit']
