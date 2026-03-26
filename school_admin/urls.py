from django.urls import path
from . import views
urlpatterns = [
    path('dashboard/',                                      views.dashboard,         name='school_admin_dashboard'),
    path('invite-management/',                              views.invite_management, name='school_admin_invite_management'),
    path('invite-management/<int:invite_id>/activate/',     views.activate_invite,   name='school_admin_activate_invite'),
    path('invite-management/<int:invite_id>/delete/',       views.delete_invite,     name='school_admin_delete_invite'),
    path('management/<int:user_id>/delete/',                views.delete_management, name='school_admin_delete_management'),
    path('management/',                                     views.management_list,   name='school_admin_management_list'),
    path('management/poll/',                                views.poll_management,   name='school_admin_poll_management'),
    path('reports/',                                        views.reports,           name='school_admin_reports'),
    path('teachers/', views.teachers_list, name='school_admin_teachers_list'),
    path('students/', views.students_list, name='school_admin_students_list'),
    path('announcements/create/', views.create_announcement, name='school_admin_create_announcement'),
]
