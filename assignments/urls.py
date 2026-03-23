from django.urls import path
from . import views
urlpatterns = [
    path('submit/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
]
