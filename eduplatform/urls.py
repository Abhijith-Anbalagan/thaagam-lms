from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Root → login
    path('', RedirectView.as_view(url='/login/', permanent=False)),

    # Auth & shared account views
    path('', include('accounts.urls')),

    # Role-based dashboards
    path('superadmin/', include('superadmin.urls')),
    path('school-admin/', include('school_admin.urls')),
    path('management/', include('management_app.urls')),

    # Teacher & classroom (teacher perspective)
    path('teacher/', include('classrooms.urls')),

    # Student
    path('student/', include('students.urls')),

    # Assignments
    path('assignments/', include('assignments.urls')),

    # Chat
    path('chat/', include('chat.urls')),

    # Announcements
    path('announcements/', include('announcements.urls')),

    # Analytics
    path('analytics/', include('analytics.urls')),
    

  
    

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
