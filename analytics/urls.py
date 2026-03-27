from django.urls import path
from . import views

urlpatterns = [
    path('teacher/', views.teacher_analytics,   name='teacher_analytics'),
    path('school/',  views.school_analytics,    name='school_analytics'),
]
