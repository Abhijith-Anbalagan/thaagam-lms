from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                              views.dashboard,      name='superadmin_dashboard'),
    path('schools/',                                views.schools_list,   name='superadmin_schools_list'),
    path('schools/<int:school_id>/',                views.school_detail,  name='superadmin_school_detail'),
    path('schools/<int:school_id>/edit/',            views.school_edit,    name='superadmin_school_edit'),
    path('schools/create/',                          views.create_school,  name='superadmin_create_school'),
    path('schools/<int:school_id>/toggle/',         views.toggle_school,  name='superadmin_toggle_school'),
    path('schools/<int:school_id>/delete/',          views.delete_school,  name='superadmin_delete_school'),
    path('admins/<int:admin_id>/delete/',            views.delete_admin,   name='superadmin_delete_admin'),
    path('courses/<int:course_id>/delete/',          views.delete_course,  name='superadmin_delete_course'),
    path('users/<int:user_id>/delete/',              views.delete_user,    name='superadmin_delete_user'),
    path('admins/',                                 views.all_admins,     name='superadmin_all_admins'),
    path('admins/<int:admin_id>/action/',            views.admin_action,   name='superadmin_admin_action'),
    path('analytics/',                               views.platform_analytics, name='superadmin_analytics'),
    path('courses/',                                views.course_list,    name='superadmin_course_list'),
    path('courses/all/',                            views.all_courses,    name='superadmin_all_courses'),
    path('courses/<int:course_id>/',                views.course_detail,  name='superadmin_course_detail'),
    path('courses/<int:course_id>/concept/add/',    views.concept_add,    name='superadmin_concept_add'),
    path('concepts/<int:concept_id>/edit/',          views.concept_edit,   name='superadmin_concept_edit'),
    path('concepts/<int:concept_id>/delete/',        views.concept_delete, name='superadmin_concept_delete'),
    path('concepts/<int:concept_id>/video/add/',     views.video_add,      name='superadmin_video_add'),
    path('videos/<int:video_id>/delete/',            views.video_delete,   name='superadmin_video_delete'),
    path('profile/', views.profile_settings, name='superadmin_profile'),
    path('api/profile/',                             views.api_profile_sync, name='api_profile_sync'),
    path('api/schools/<int:school_id>/edit/', views.api_school_edit, name='api_school_edit'),
    
]