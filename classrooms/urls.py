from django.urls import path
from classrooms.views.teacher_views import (
    teacher_dashboard,
    create_classroom,
    my_classrooms,
    my_learning,
    teacher_announcements,
    post_announcement,
    classroom_announce,
    classroom_courses,
    classroom_classwork,
    classroom_peoples,
    classroom_grade,
    classroom_chat,
)

urlpatterns = [
    path('dashboard/',                               teacher_dashboard,   name='teacher_dashboard'),
    path('create-classroom/',                        create_classroom,    name='teacher_create_classroom'),
    path('my-classrooms/',                           my_classrooms,       name='teacher_my_classrooms'),
    path('my-learning/',                             my_learning,         name='teacher_my_learning'),
    path('announcements/',                           teacher_announcements, name='teacher_announcements'),
    path('announce/',                                post_announcement,   name='teacher_post_announcement'),
    path('classroom/<int:classroom_id>/announce/',   classroom_announce,  name='teacher_classroom_announce'),
    path('classroom/<int:classroom_id>/courses/',    classroom_courses,   name='teacher_classroom_courses'),
    path('classroom/<int:classroom_id>/classwork/',  classroom_classwork, name='teacher_classroom_classwork'),
    path('classroom/<int:classroom_id>/peoples/',    classroom_peoples,   name='teacher_classroom_peoples'),
    path('classroom/<int:classroom_id>/grades/',     classroom_grade,     name='teacher_classroom_grade'),
    path('classroom/<int:classroom_id>/chat/',       classroom_chat,      name='teacher_classroom_chat'),
]
