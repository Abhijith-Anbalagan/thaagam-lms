from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                              views.dashboard,          name='student_dashboard'),
    path('join/',                                   views.join_class,         name='student_join_class'),
    path('leave/<int:class_id>/',                   views.leave_classroom,    name='student_leave_classroom'),
    path('classroom/<int:class_id>/announce/',      views.classroom_announce, name='student_classroom_announce'),
    path('classroom/<int:class_id>/courses/',       views.classroom_courses,  name='student_classroom_courses'),
    path('classroom/<int:class_id>/classwork/',     views.classroom_classwork,name='student_classroom_classwork'),
    path('classroom/<int:class_id>/peoples/',       views.classroom_peoples,  name='student_classroom_peoples'),
    path('classroom/<int:class_id>/grades/',        views.classroom_grade,    name='student_classroom_grade'),
    path('classroom/<int:class_id>/chat/',          views.classroom_chat,     name='student_classroom_chat'),
]
