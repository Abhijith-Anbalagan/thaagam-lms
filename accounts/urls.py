from django.urls import path
from . import views

urlpatterns = [
    path('signup/',         views.signup_view,          name='signup'),
    path('login/',          views.login_view,           name='login'),
    path('logout/',         views.logout_view,          name='logout'),
    path('public-dashboard/', views.public_dashboard,  name='public_dashboard'),
    path('accept-invite/<uuid:token>/', views.accept_invite_view, name='accept_invite'),
    path('profile/',        views.profile_view,         name='profile'),
    path('profile/password/', views.password_change_view, name='password_change'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uuid:token>/', views.reset_password_view, name='reset_password'),
]
