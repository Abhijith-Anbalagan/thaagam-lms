from django.urls import path
from classrooms.views.teacher_views import (
    teacher_dashboard,
    create_classroom,
    my_classrooms,
    my_learning,
    teacher_course_detail,
    course_enroll,
    teacher_messages,
    teacher_announcements,
    post_announcement,
    classroom_announce,
    classroom_courses,
    classroom_classwork,
    classroom_peoples,
    classroom_grade,
    classroom_chat,
    classroom_detail,
    assign_course_to_classroom,
)

urlpatterns = [
    path('dashboard/',                                                      teacher_dashboard,           name='teacher_dashboard'),
    path('create-classroom/',                                               create_classroom,            name='teacher_create_classroom'),
    path('my-classrooms/',                                                  my_classrooms,               name='teacher_my_classrooms'),
    path('my-learning/',                                                    my_learning,                 name='teacher_my_learning'),
    path('my-learning/<int:course_id>/',                                    teacher_course_detail,       name='teacher_course_detail'),
    path('my-learning/<int:course_id>/enroll/',                             course_enroll,               name='teacher_course_enroll'),
    path('messages/',                                                       teacher_messages,            name='teacher_messages'),
    path('announcements/',                                                  teacher_announcements,       name='teacher_announcements'),
    path('announce/',                                                       post_announcement,           name='teacher_post_announcement'),

    # Classroom detail (overview) — must come BEFORE the sub-paths below
    path('classroom/<int:classroom_id>/',                                   classroom_detail,            name='teacher_classroom_detail'),
    path('classroom/<int:classroom_id>/assign-course/<int:course_id>/',     assign_course_to_classroom,  name='teacher_assign_course'),

    # Classroom tab views
    path('classroom/<int:classroom_id>/announce/',                          classroom_announce,          name='teacher_classroom_announce'),
    path('classroom/<int:classroom_id>/courses/',                           classroom_courses,           name='teacher_classroom_courses'),
    path('classroom/<int:classroom_id>/classwork/',                         classroom_classwork,         name='teacher_classroom_classwork'),
    path('classroom/<int:classroom_id>/peoples/',                           classroom_peoples,           name='teacher_classroom_peoples'),
    path('classroom/<int:classroom_id>/grades/',                            classroom_grade,             name='teacher_classroom_grade'),
    path('classroom/<int:classroom_id>/chat/',                              classroom_chat,              name='teacher_classroom_chat'),
]
