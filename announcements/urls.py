from django.urls import path
from . import views

urlpatterns = [
    path('school-wide/', views.school_wide_list, name='announcements_school_wide'),
    path('feed/',        views.student_feed,     name='announcements_feed'),
]
