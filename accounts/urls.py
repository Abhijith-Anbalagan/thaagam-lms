from django.urls import path
from . import views

urlpatterns = [
    path('signup/',           views.signup_view,          name='signup'),
    path('login/',            views.login_view,           name='login'),
    path('logout/',           views.logout_view,          name='logout'),
    path('public-dashboard/', views.public_dashboard,     name='public_dashboard'),

    # Invite flow
    path('accept-invite/<uuid:token>/', views.accept_invite_view, name='accept_invite'),
    

    # Email verification
    path('verify-email/<uuid:token>/',  views.verify_email_view,  name='verify_email'),

    # Forgot / reset password
    path('forgot-password/',                    views.forgot_password_view,             name='forgot_password'),
    path('reset-password/<uuid:token>/',        views.reset_password_view,              name='reset_password'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    
    
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
]