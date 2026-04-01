from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('signup/',           views.signup_view,            name='signup'),
    path('login/',            views.login_view,             name='login'),
    path('logout/',           views.logout_view,            name='logout'),
    path('forgot-password/',  views.forgot_password_view,   name='forgot_password'),
    path('public-dashboard/', views.public_dashboard,       name='public_dashboard'),
    path('accept-invite/<uuid:token>/', views.accept_invite_view, name='accept_invite'),
    path('profile/',          views.profile_view,           name='profile'),
    path('profile/password/', views.password_change_view,   name='password_change'),
     path('contact/', views.contact_us, name='contact_us'),

    # ✅ Add these missing ones
    path('verify-email/<uuid:token>/', views.verify_email_view,     name='verify_email'),
    
    path('resend-verification/',       views.resend_verification_view, name='resend_verification'),
    
   path('reset-password/<uuid:token>/', views.reset_password_view,  name='reset_password'),
   
   path('testimonial/submit/', views.submit_testimonial, name='submit_testimonial'),
   path('testimonial/manage/', views.manage_testimonials, name='manage_testimonials'),
]
