from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                              views.dashboard,           name='student_dashboard'),
    path('join/',                                   views.join_class,          name='student_join_class'),
    path('leave/<int:class_id>/',                   views.leave_classroom,     name='student_leave_classroom'),
    path('classroom/<int:class_id>/announce/',      views.classroom_announce,  name='student_classroom_announce'),
    path('classroom/<int:class_id>/courses/',       views.classroom_courses,   name='student_classroom_courses'),
    path('classroom/<int:class_id>/classwork/',     views.classroom_classwork, name='student_classroom_classwork'),
    path('classroom/<int:class_id>/peoples/',       views.classroom_peoples,   name='student_classroom_peoples'),
    path('classroom/<int:class_id>/grades/',        views.classroom_grade,     name='student_classroom_grade'),
    path('classroom/<int:class_id>/chat/',          views.classroom_chat,      name='student_classroom_chat'),
    path('api/unread-count/',                       views.unread_count_api,    name='student_unread_count'),
    path('api/pending-count/',                      views.pending_count_api,   name='student_pending_count'),
    path('api/graded-count/',                       views.graded_count_api,    name='student_graded_count'),
    path('api/new-grades-count/',                   views.new_grades_count_api, name='student_new_grades_count'),
    path('api/course-count/',                       views.course_count_api,    name='student_course_count'),
    path('api/course-enroll/<int:course_id>/',      views.course_enroll,       name='student_course_enroll'),
    path('my-learning/',                            views.my_learning,         name='student_my_learning'),
    path('my-learning/<int:course_id>/',            views.course_detail,       name='student_course_detail'),
    path('api/concept-complete/<int:concept_id>/',  views.concept_complete,    name='student_concept_complete'),
]
