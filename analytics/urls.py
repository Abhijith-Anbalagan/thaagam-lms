from django.urls import path
from . import views
from .management_views import management_analytics_excel

urlpatterns = [
    # Super Admin Analytics
    path('superadmin/', views.superadmin_analytics, name='analytics_superadmin'),

    # School Admin Analytics
    path('school-admin/', views.school_admin_analytics, name='school_admin_analytics'),

    # Management Analytics
    path('management/', views.management_analytics, name='management_analytics'),
    path('management/excel/', management_analytics_excel, name='management_analytics_excel'),

    # Teacher Analytics
    path('teacher/', views.teacher_analytics, name='teacher_analytics'),
    path('teacher/export/', views.export_overall_analytics, name='export_overall_analytics'),
    path('teacher/classroom/<int:classroom_id>/', views.classroom_analytics, name='teacher_classroom_analytics'),
    path('teacher/classroom/<int:classroom_id>/export/', views.export_classroom_analytics, name='export_classroom_analytics'),

    # Student Analytics
    path('student/', views.student_analytics, name='student_analytics'),
    path('student/assignment-tracking/', views.student_assignment_tracking, name='student_assignment_tracking'),

    # Legacy URLs for backward compatibility
    path('school/', views.school_admin_analytics, name='school_analytics'),
]
