from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('dashboard/', views.student_dashboard, name='dashboard'),
    path('join-classroom/', views.join_classroom, name='join_classroom'),
    path('classroom/<int:id>/announce/', views.classroom_announce, name='classroom_announce'),
    path('classroom/<int:id>/courses/', views.classroom_courses, name='classroom_courses'),
    path('classroom/<int:id>/classwork/', views.classroom_classwork, name='classroom_classwork'),
    path('classroom/<int:id>/peoples/', views.classroom_peoples, name='classroom_peoples'),
    path('classroom/<int:id>/grades/', views.classroom_grades, name='classroom_grades'),
    path('classroom/<int:id>/chat/', views.classroom_chat, name='classroom_chat'),
    path('assignment/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),
]