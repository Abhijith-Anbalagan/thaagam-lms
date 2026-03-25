from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import uuid
from classrooms.models import Classroom
from .models import User, Invitation
from .emails import send_verification_email, send_password_reset_email  # ✅ centralised email helpers
from .forms import (
    SignupForm, LoginForm, AcceptInviteForm, ProfileForm,
    ForgotPasswordForm, ResetPasswordForm,
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
        send_verification_email(user, verification_url)  # ✅ uses helper

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

    return render(request, 'accounts/login.html', {'form': form})


# ─── Logout ───────────────────────────────────────────────────────────────────

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
    # ✅ Fix 3 — invalid token shows clean page instead of ugly 404
    try:
        invite = Invitation.objects.get(token=token)
    except Invitation.DoesNotExist:
        return render(request, 'accounts/invite_invalid.html')

    # ✅ Fix 4 — expired or already accepted
    if not invite.is_valid:
        return render(request, 'accounts/invite_expired.html')

    # ✅ Fix 1 — email already registered
    if User.objects.filter(email=invite.email).exists():
        return render(request, 'accounts/invite_already_used.html', {
            'email': invite.email
        })

    if request.method == 'POST':
        form = AcceptInviteForm(request.POST)
        if form.is_valid():
            username  = form.cleaned_data['username'].strip()
            password  = form.cleaned_data['password1']

            # ✅ Fix 6 — empty username after stripping whitespace
            if not username:
                form.add_error('username', 'Username cannot be blank')
                return render(request, 'accounts/accept_invite.html', {
                    'form': form, 'invitation': invite
                })

            # ✅ Fix 5 — password strength validation
            try:
                validate_password(password)
            except ValidationError as e:
                form.add_error('password1', e)
                return render(request, 'accounts/accept_invite.html', {
                    'form': form, 'invitation': invite
                })

            # ✅ Fix 1 — double check email uniqueness before save
            if User.objects.filter(email=invite.email).exists():
                form.add_error(None, 'This email is already registered.')
                return render(request, 'accounts/accept_invite.html', {
                    'form': form, 'invitation': invite
                })

            # All good — create user
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
            return redirect('/login/')

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
    messages.success(request, 'Email verified successfully! Welcome to EduPlatform.')
    return redirect('/public-dashboard/')


# ─── Forgot Password ──────────────────────────────────────────────────────────

def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    form = ForgotPasswordForm(request.POST or None)
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
            send_password_reset_email(user, reset_url)  # ✅ uses helper

        except User.DoesNotExist:
            pass  # Silently succeed — don't reveal whether account exists

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

    return render(request, 'accounts/reset_password.html', {'form': form, 'token': token})


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'shared/profile_settings.html', {'form': form})


# ─── Resend Verification ──────────────────────────────────────────────────────

def resend_verification_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
    elif request.method == 'GET':
        email = request.GET.get('email', '').strip()
    else:
        return redirect('signup')

    if email:
        try:
            user = User.objects.get(email__iexact=email, is_active=False, email_verified=False)
            user.email_verification_token      = uuid.uuid4()
            user.email_verification_expires_at = timezone.now() + timedelta(hours=24)
            user.save()

            verification_url = request.build_absolute_uri(
                reverse('verify_email', args=[user.email_verification_token])
            )
            send_verification_email(user, verification_url)  # ✅ uses helper

        except User.DoesNotExist:
            pass  # Silently succeed — don't reveal whether account exists

    return render(request, 'accounts/email_verification_sent.html', {
        'email':  email,
        'resent': True,
    })