from django.urls import path
from . import views
urlpatterns = [
    path('dashboard/',         views.dashboard,       name='school_admin_dashboard'),
    path('invite-management/', views.invite_management, name='school_admin_invite_management'),
    path('management/',        views.management_list, name='school_admin_management_list'),
    path('reports/',           views.reports,         name='school_admin_reports'),
]
