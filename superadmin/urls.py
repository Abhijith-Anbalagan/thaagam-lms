from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',          views.dashboard,         name='superadmin_dashboard'),
    path('schools/',            views.schools_list,      name='superadmin_schools_list'),
    path('schools/<int:school_id>/', views.school_detail, name='superadmin_school_detail'),
    path('schools/create/',     views.create_school,     name='superadmin_create_school'),
    path('schools/<int:school_id>/toggle/', views.toggle_school, name='superadmin_toggle_school'),
    path('admins/',             views.all_admins,        name='superadmin_all_admins'),
    path('admins/create/',      views.create_school_admin, name='superadmin_create_school_admin'),
    path('courses/create/',     views.course_create,     name='superadmin_course_create'),
]
