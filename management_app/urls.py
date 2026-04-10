from django.urls import path
from . import views
urlpatterns = [
    path('dashboard/',      views.dashboard,     name='management_dashboard'),
    path('invite-teacher/', views.invite_teacher, name='management_invite_teacher'),
    path('teachers/',       views.teachers_list,  name='management_teachers_list'),
    path('announcements/',  views.announcements_management, name='management_announcements'),
    path('announcements/<str:mode>/', views.announcements_detail, name='management_announcements_detail'),
]
