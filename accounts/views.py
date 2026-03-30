import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from classrooms.models import Classroom
from .models import User, Invitation
from .forms import (
    SignupForm, LoginForm, AcceptInviteForm,
    ProfileForm, PasswordChangeCustomForm,
    ForgotPasswordForm, ResetPasswordForm,
)

from django.core.mail import send_mail
from django.http import JsonResponse
import json

def contact_us(request):
    if request.method == 'POST':
        try:
            data    = json.loads(request.body)
            email   = data.get('email', '').strip()
            message = data.get('message', '').strip()

            if not email or not message:
                return JsonResponse({'status': 'error', 'msg': 'All fields required.'}, status=400)

            send_mail(
                subject        = f'New Message from {email}',
                message        = f'From: {email}\n\n{message}',
                from_email     = 'noreply@eduplatform.com',
                recipient_list = ['johnweslee07@gmail.com'],  # ← your johnGmail inbox
                fail_silently  = False,
            )
            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)

    return JsonResponse({'status': 'method not allowed'}, status=405)


# ─── Email Helpers ────────────────────────────────────────────────────────────
def landing_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    return render(request, 'accounts/landing.html')  # ← update path



def send_verification_email(user, verification_url):
    send_mail(
        subject        = 'Verify your EduPlatform email',
        message        = f'Hi {user.username},\n\nClick to verify your account:\n{verification_url}\n\nExpires in 24 hours.',
        from_email     = 'noreply@eduplatform.com',
        recipient_list = [user.email],
    )


def send_password_reset_email(user, reset_url):
    send_mail(
        subject        = 'Reset your EduPlatform password',
        message        = f'Hi {user.username},\n\nClick to reset your password:\n{reset_url}\n\nExpires in 2 hours.\n\nIf you did not request this, ignore this email.',
        from_email     = 'noreply@eduplatform.com',
        recipient_list = [user.email],
    )


# ─── Signup ───────────────────────────────────────────────────────────────────

def signup_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.email_verification_token      = uuid.uuid4()
        user.email_verification_expires_at = timezone.now() + timedelta(hours=24)
        user.save()

        verification_url = request.build_absolute_uri(
            reverse('verify_email', args=[user.email_verification_token])
        )
        send_verification_email(user, verification_url)

        return render(request, 'accounts/email_verification_sent.html', {'email': user.email})

    return render(request, 'accounts/signup.html', {'form': form})


# ─── Login ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(user.get_dashboard_url())

    return render(request, 'registration/login.html', {'form': form})


# ─── Logout ───────────────────────────────────────────────────────────────────

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect(reverse('login'))


# ─── Public Dashboard ─────────────────────────────────────────────────────────

@login_required
def public_dashboard(request):
    error = None
    if request.method == 'POST':
        code = request.POST.get('class_code', '').strip().upper()
        try:
            classroom = Classroom.objects.get(code=code)
            classroom.students.add(request.user)
            request.user.role   = 'student'
            request.user.school = classroom.school
            request.user.save()
            messages.success(request, f'You joined {classroom.name}!')
            return redirect('/student/dashboard/')
        except Classroom.DoesNotExist:
            error = 'Class code not found. Try again.'
    return render(request, 'accounts/public_dashboard.html', {'error': error})


# ─── Accept Invite ────────────────────────────────────────────────────────────

def accept_invite_view(request, token):
    try:
        invite = Invitation.objects.get(token=token)
    except Invitation.DoesNotExist:
        return render(request, 'accounts/invite_invalid.html')

    if not invite.is_valid:
        return render(request, 'accounts/invite_expired.html')

    if User.objects.filter(email=invite.email).exists():
        return render(request, 'accounts/invite_already_used.html', {
            'email': invite.email
        })

    if request.method == 'POST':
        form = AcceptInviteForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password1']

            if not username:
                form.add_error('username', 'Username cannot be blank')
                return render(request, 'accounts/accept_invite.html', {
                    'form': form, 'invitation': invite
                })

            try:
                validate_password(password)
            except ValidationError as e:
                form.add_error('password1', e)
                return render(request, 'accounts/accept_invite.html', {
                    'form': form, 'invitation': invite
                })

            if User.objects.filter(email=invite.email).exists():
                form.add_error(None, 'This email is already registered.')
                return render(request, 'accounts/accept_invite.html', {
                    'form': form, 'invitation': invite
                })

            user = User.objects.create_user(
                username       = username,
                email          = invite.email,
                password       = password,
                role           = invite.role,
                school         = invite.school,
                email_verified = True,
            )

            invite.accepted = True
            invite.save()

            messages.success(request, 'Account created! You can now log in.')
            return redirect('login')

    else:
        form = AcceptInviteForm()

    return render(request, 'accounts/accept_invite.html', {
        'form':       form,
        'invitation': invite,
    })


# ─── Email Verification ───────────────────────────────────────────────────────

def verify_email_view(request, token):
    try:
        user = User.objects.get(email_verification_token=token)
    except User.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('login')

    if not user.is_email_verification_valid:
        messages.error(request, 'Verification link has expired.')
        return redirect('resend_verification')

    user.is_active                     = True
    user.email_verified                = True
    user.email_verification_token      = None
    user.email_verification_expires_at = None
    user.save()

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, 'Email verified! Welcome to EduPlatform.')
    return redirect(user.get_dashboard_url())


# ─── Resend Verification ──────────────────────────────────────────────────────

def resend_verification_view(request):
    email = request.GET.get('email') or request.POST.get('email')

    if not email:
        return redirect('login')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, 'No account found with that email.')
        return redirect('login')

    if user.email_verified:
        messages.success(request, 'Your email is already verified. Please login.')
        return redirect('login')

    user.email_verification_token      = uuid.uuid4()
    user.email_verification_expires_at = timezone.now() + timedelta(hours=24)
    user.save()

    verification_url = request.build_absolute_uri(
        reverse('verify_email', args=[user.email_verification_token])
    )
    send_verification_email(user, verification_url)

    messages.success(request, 'Verification email resent! Check your inbox.')
    return render(request, 'accounts/email_verification_sent.html', {'email': email})


# ─── Forgot Password ──────────────────────────────────────────────────────────

def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    form        = ForgotPasswordForm(request.POST or None)
    email_sent  = False
    reset_email = None

    if request.method == 'POST' and form.is_valid():
        email       = form.cleaned_data['email']
        reset_email = email
        email_sent  = True

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
            user.password_reset_token      = uuid.uuid4()
            user.password_reset_expires_at = timezone.now() + timedelta(hours=2)
            user.save()

            reset_url = request.build_absolute_uri(
                reverse('reset_password', args=[user.password_reset_token])
            )
            send_password_reset_email(user, reset_url)

        except User.DoesNotExist:
            pass  # silently succeed — don't reveal if account exists

    return render(request, 'accounts/forgot_password.html', {
        'form':        form,
        'email_sent':  email_sent,
        'reset_email': reset_email,
    })


# ─── Reset Password ───────────────────────────────────────────────────────────

def reset_password_view(request, token):
    try:
        user = User.objects.get(password_reset_token=token)
    except User.DoesNotExist:
        messages.error(request, 'Invalid or expired reset link.')
        return redirect('login')

    if not user.is_password_reset_valid:
        messages.error(request, 'This reset link has expired. Please request a new one.')
        return redirect('forgot_password')

    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['password1'])
        user.password_reset_token      = None
        user.password_reset_expires_at = None
        user.save()
        messages.success(request, 'Password reset successfully. You can now sign in.')
        return redirect('login')

    return render(request, 'accounts/reset_password.html', {
        'form':  form,
        'token': token,
    })


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'shared/profile_settings.html', {'form': form})


@login_required
def password_change_view(request):
    form = PasswordChangeCustomForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')
    return render(request, 'shared/profile_settings.html', {
        'form':    request.user,
        'pw_form': form,
        'show_pw': True,
    })
    
    
