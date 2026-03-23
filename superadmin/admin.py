from django.contrib import admin
from .models import School, GlobalCourse

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter  = ['is_active']

@admin.register(GlobalCourse)
class GlobalCourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'school', 'status', 'created_by']
