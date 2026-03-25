from django.contrib import admin
from .models import School, GlobalCourse, GlobalConcept, GlobalConceptVideo

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter  = ['is_active']

@admin.register(GlobalCourse)
class GlobalCourseAdmin(admin.ModelAdmin):
    list_display      = ['title', 'status', 'created_by', 'created_at']
    filter_horizontal = ['schools']

@admin.register(GlobalConcept)
class GlobalConceptAdmin(admin.ModelAdmin):
    list_display = ['header', 'course', 'order', 'created_at']

@admin.register(GlobalConceptVideo)
class GlobalConceptVideoAdmin(admin.ModelAdmin):
    list_display = ['concept', 'title', 'order']