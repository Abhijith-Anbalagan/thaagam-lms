from django.urls import path
from . import views

urlpatterns = [
    # Super Admin Analytics
    path('superadmin/', views.superadmin_analytics, name='superadmin_analytics'),

    # School Admin Analytics
    path('school-admin/', views.school_admin_analytics, name='school_admin_analytics'),

    # Management Analytics
    path('management/', views.management_analytics, name='management_analytics'),

    # Teacher Analytics
    path('teacher/', views.teacher_analytics, name='teacher_analytics'),

    # Student Analytics
    path('student/', views.student_analytics, name='student_analytics'),
    path('student/assignment-tracking/', views.student_assignment_tracking, name='student_assignment_tracking'),

    # Legacy URLs for backward compatibility
    path('school/', views.school_admin_analytics, name='school_analytics'),
]
