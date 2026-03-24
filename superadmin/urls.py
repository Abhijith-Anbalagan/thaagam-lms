from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                              views.dashboard,      name='superadmin_dashboard'),
    path('schools/',                                views.schools_list,   name='superadmin_schools_list'),
    path('schools/<int:school_id>/',                views.school_detail,  name='superadmin_school_detail'),
    path('schools/<int:school_id>/edit/',            views.school_edit,    name='superadmin_school_edit'),
    path('schools/create/',                          views.create_school,  name='superadmin_create_school'),
    path('schools/<int:school_id>/toggle/',         views.toggle_school,  name='superadmin_toggle_school'),
    path('admins/',                                 views.all_admins,     name='superadmin_all_admins'),
    path('courses/',                                views.course_list,    name='superadmin_course_list'),
    path('courses/<int:course_id>/',                views.course_detail,  name='superadmin_course_detail'),
    path('courses/<int:course_id>/concept/add/',    views.concept_add,    name='superadmin_concept_add'),
]
