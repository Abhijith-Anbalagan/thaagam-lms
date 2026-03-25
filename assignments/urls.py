from django.urls import path
from . import views

# Registered in main urls.py under path('assignments/', include('assignments.urls'))
urlpatterns = [
    path('<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
]
