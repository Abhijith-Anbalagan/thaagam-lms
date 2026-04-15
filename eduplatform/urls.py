from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path
from django.http import HttpResponse

def favicon(request):
    # 1x1 transparent ICO — stops 404 noise in logs
    ico = (b'\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00'
           b'\x18\x00(\x00\x00\x00\x16\x00\x00\x00(\x00\x00\x00'
           b'\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x18\x00'
           b'\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00'
           b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
           b'\xff\xff\xff\x00\x00\x00\x00\x00')
    return HttpResponse(ico, content_type='image/x-icon')

urlpatterns = [
    path('favicon.ico', favicon),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('superadmin/', include('superadmin.urls')),
    path('school-admin/', include('school_admin.urls')),
    path('management/', include('management_app.urls')),
    path('teacher/', include('classrooms.urls')),
    path('student/', include('students.urls')),
    path('assignments/', include('assignments.urls')),
    path('chat/', include('chat.urls')),
    path('announcements/', include('announcements.urls')),
    path('analytics/', include('analytics.urls')),

    path('rag/', include('rag.urls')),

]
# Always serve media files in development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)