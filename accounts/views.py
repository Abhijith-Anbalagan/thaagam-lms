import uuid
from datetime import timedelta
from .models import User, Invitation, Testimonial   
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail, EmailMultiAlternatives  # ← fixed
from django.forms import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string              # ← added
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from django.contrib.auth import login, logout, update_session_auth_hash

from classrooms.models import Classroom
from .models import User, Invitation
from .forms import (
    SignupForm, LoginForm, AcceptInviteForm,
    ProfileForm, PasswordChangeCustomForm,
    ForgotPasswordForm, ResetPasswordForm,
)
from .models import Testimonial
from .forms import TestimonialForm


# ─── Contact Us ───────────────────────────────────────────────────────────────

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
                recipient_list = ['johnweslee07@gmail.com'],
                fail_silently  = False,
            )
            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)

    return JsonResponse({'status': 'method not allowed'}, status=405)


# ─── Landing ──────────────────────────────────────────────────────────────────

def landing_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    return render(request, 'accounts/landing.html')


# ─── Email Helpers ────────────────────────────────────────────────────────────

# ─── Email Helpers ────────────────────────────────────────────────────────────

def send_verification_email(user, verification_url):
    subject = 'Verify your EduPlatform email'

    plain = (
        f'Hi {user.username},\n\n'
        f'Click to verify your account:\n{verification_url}\n\n'
        f'Expires in 24 hours.'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
</head>
<body style="margin:0;padding:0;background-color:#f7f6f2;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f7f6f2;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table width="560" cellpadding="0" cellspacing="0" border="0"
               style="max-width:560px;width:100%;background-color:#ffffff;
                      border-radius:12px;border:1px solid #e8e6e0;
                      box-shadow:0 4px 16px rgba(0,0,0,0.08);">

          <!-- Accent stripe -->
          <tr>
            <td style="height:5px;
                       background:linear-gradient(90deg,#c8401a 0%,#e8642e 55%,#f5a623 100%);
                       border-radius:12px 12px 0 0;font-size:0;line-height:0;">&nbsp;</td>
          </tr>

          <!-- Header -->
          <tr>
            <td style="background-color:#1a1f36;padding:24px 36px;border-radius:0;">
              <span style="color:#ffffff;font-size:18px;font-weight:700;
                           font-family:'Segoe UI',Arial,sans-serif;">
                Edu<span style="color:#c8401a;">Platform</span>
              </span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px;">
              <h2 style="margin:0 0 8px;font-size:22px;font-weight:700;
                         color:#1a1f36;font-family:'Segoe UI',Arial,sans-serif;">
                Verify your email address
              </h2>
              <p style="margin:0 0 20px;font-size:14px;color:#7a7470;
                        font-family:'Segoe UI',Arial,sans-serif;">
                Hi <strong style="color:#0f0e0d;">{user.username}</strong>,
                thanks for signing up!
              </p>
              <p style="margin:0 0 28px;font-size:15px;color:#3d3d3a;
                        line-height:1.7;font-family:'Segoe UI',Arial,sans-serif;">
                Click the button below to verify your email address and
                activate your EduPlatform account.
              </p>

              <!-- Button -->
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td align="center" style="padding:4px 0 32px;">
                    <a href="{verification_url}"
                       style="display:inline-block;background-color:#c8401a;
                              color:#ffffff;text-decoration:none;
                              padding:14px 36px;border-radius:10px;
                              font-size:15px;font-weight:600;
                              font-family:'Segoe UI',Arial,sans-serif;">
                      &#10003;&nbsp; Verify Email Address
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Fallback URL -->
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td style="background-color:#f7f6f2;border-radius:10px;
                             padding:14px 18px;border:1px solid #e8e6e0;">
                    <p style="margin:0 0 5px;font-size:12px;font-weight:600;
                               color:#7a7470;text-transform:uppercase;
                               letter-spacing:0.08em;
                               font-family:'Segoe UI',Arial,sans-serif;">
                      Button not working?
                    </p>
                    <p style="margin:0;font-size:12px;color:#7a7470;
                              font-family:'Segoe UI',Arial,sans-serif;line-height:1.5;">
                      Copy and paste this link into your browser:<br>
                      <a href="{verification_url}"
                         style="color:#c8401a;word-break:break-all;font-size:11px;">
                        {verification_url}
                      </a>
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Expiry -->
              <table cellpadding="0" cellspacing="0" border="0" width="100%"
                     style="margin-top:20px;">
                <tr>
                  <td style="border-top:1px solid #e8e6e0;padding-top:18px;">
                    <p style="margin:0;font-size:13px;color:#7a7470;line-height:1.6;
                              font-family:'Segoe UI',Arial,sans-serif;">
                      &#9203;&nbsp; This link expires in
                      <strong style="color:#0f0e0d;">24 hours</strong>.<br>
                      If you didn&#39;t create an account, you can safely ignore this email.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f7f6f2;padding:18px 36px;
                       border-top:1px solid #e8e6e0;border-radius:0 0 12px 12px;">
              <p style="margin:0;font-size:12px;color:#9e9c95;
                        font-family:'Segoe UI',Arial,sans-serif;">
                &copy; EduPlatform &nbsp;&middot;&nbsp;
                You&#39;re receiving this because you signed up at EduPlatform.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email='noreply@eduplatform.com',
        to=[user.email],
    )
    email.attach_alternative(html, "text/html")
    email.send(fail_silently=False)


def send_password_reset_email(user, reset_url):
    subject = 'Reset your EduPlatform password'

    plain = (
        f'Hi {user.username},\n\n'
        f'Click to reset your password:\n{reset_url}\n\n'
        f'Expires in 2 hours.\n\n'
        f'If you did not request this, ignore this email.'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
</head>
<body style="margin:0;padding:0;background-color:#f7f6f2;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f7f6f2;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table width="560" cellpadding="0" cellspacing="0" border="0"
               style="max-width:560px;width:100%;background-color:#ffffff;
                      border-radius:12px;border:1px solid #e8e6e0;
                      box-shadow:0 4px 16px rgba(0,0,0,0.08);">

          <!-- Accent stripe -->
          <tr>
            <td style="height:5px;
                       background:linear-gradient(90deg,#1d5fa8 0%,#3b82f6 55%,#60a5fa 100%);
                       border-radius:12px 12px 0 0;font-size:0;line-height:0;">&nbsp;</td>
          </tr>

          <!-- Header -->
          <tr>
            <td style="background-color:#1a1f36;padding:24px 36px;">
              <span style="color:#ffffff;font-size:18px;font-weight:700;
                           font-family:'Segoe UI',Arial,sans-serif;">
                Edu<span style="color:#c8401a;">Platform</span>
              </span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px;">
              <h2 style="margin:0 0 8px;font-size:22px;font-weight:700;
                         color:#1a1f36;font-family:'Segoe UI',Arial,sans-serif;">
                Reset your password
              </h2>
              <p style="margin:0 0 20px;font-size:14px;color:#7a7470;
                        font-family:'Segoe UI',Arial,sans-serif;">
                Hi <strong style="color:#0f0e0d;">{user.username}</strong>
              </p>
              <p style="margin:0 0 28px;font-size:15px;color:#3d3d3a;
                        line-height:1.7;font-family:'Segoe UI',Arial,sans-serif;">
                We received a request to reset your EduPlatform password.
                Click the button below to choose a new one.
              </p>

              <!-- Button -->
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td align="center" style="padding:4px 0 32px;">
                    <a href="{reset_url}"
                       style="display:inline-block;background-color:#1d5fa8;
                              color:#ffffff;text-decoration:none;
                              padding:14px 36px;border-radius:10px;
                              font-size:15px;font-weight:600;
                              font-family:'Segoe UI',Arial,sans-serif;">
                      &#128274;&nbsp; Reset Password
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Fallback URL -->
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td style="background-color:#f7f6f2;border-radius:10px;
                             padding:14px 18px;border:1px solid #e8e6e0;">
                    <p style="margin:0 0 5px;font-size:12px;font-weight:600;
                               color:#7a7470;text-transform:uppercase;
                               letter-spacing:0.08em;
                               font-family:'Segoe UI',Arial,sans-serif;">
                      Button not working?
                    </p>
                    <p style="margin:0;font-size:12px;color:#7a7470;
                              font-family:'Segoe UI',Arial,sans-serif;line-height:1.5;">
                      Copy and paste this link into your browser:<br>
                      <a href="{reset_url}"
                         style="color:#1d5fa8;word-break:break-all;font-size:11px;">
                        {reset_url}
                      </a>
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Expiry -->
              <table cellpadding="0" cellspacing="0" border="0" width="100%"
                     style="margin-top:20px;">
                <tr>
                  <td style="border-top:1px solid #e8e6e0;padding-top:18px;">
                    <p style="margin:0;font-size:13px;color:#7a7470;line-height:1.6;
                              font-family:'Segoe UI',Arial,sans-serif;">
                      &#9203;&nbsp; This link expires in
                      <strong style="color:#0f0e0d;">2 hours</strong>.<br>
                      If you didn&#39;t request this, your password will not be changed.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f7f6f2;padding:18px 36px;
                       border-top:1px solid #e8e6e0;border-radius:0 0 12px 12px;">
              <p style="margin:0;font-size:12px;color:#9e9c95;
                        font-family:'Segoe UI',Arial,sans-serif;">
                &copy; EduPlatform &nbsp;&middot;&nbsp;
                You&#39;re receiving this because a reset was requested for your account.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email='noreply@eduplatform.com',
        to=[user.email],
    )
    email.attach_alternative(html, "text/html")
    email.send(fail_silently=False)


# ─── Signup ───────────────────────────────────────────────────────────────────

def signup_view(request):                                        # ← restored
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
    if request.user.is_authenticated:
        logout(request)
        return redirect(request.get_full_path())
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
            pass

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
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            # ← refresh user from DB so avatar shows immediately
            request.user.refresh_from_db()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ProfileForm(instance=request.user)

    base_template = 'base.html'
    context = {
        'form'   : form,
        'pw_form': PasswordChangeCustomForm(request.user),
    }

    if request.user.role == 'student':
        base_template = 'student/base_student.html'
        try:
            from students.views import _student_layout_context
            context.update(_student_layout_context(request))
        except ImportError:
            pass

    context['base_template'] = base_template
    return render(request, 'shared/profile_settings.html', context)

@login_required
def password_change_view(request):
    form = PasswordChangeCustomForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')
    
    base_template = 'base.html'
    context = {
        'form':    request.user,
        'pw_form': form,
        'show_pw': True,
    }

    if request.user.role == 'student':
        base_template = 'student/base_student.html'
        try:
            from students.views import _student_layout_context
            context.update(_student_layout_context(request))
        except ImportError:
            pass

    context['base_template'] = base_template
    return render(request, 'shared/profile_settings.html', context)
        
def landing(request):
    testimonials = Testimonial.objects.filter(status='approved').order_by('-created_at')
    return render(request, 'accounts/landing.html', {'testimonials': testimonials})
# ✅ Public — no login required 
def submit_testimonial(request):
    if request.method == 'POST':
        form = TestimonialForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'accounts/testimonial_success.html')
    else:
        form = TestimonialForm()
    return render(request, 'accounts/submit_testimonial.html', {'form': form})

# 🔒 Admin only
@login_required
def manage_testimonials(request):
    if request.method == 'POST':
        testimonial_id = request.POST.get('id')
        action = request.POST.get('action')
        testimonial = get_object_or_404(Testimonial, id=testimonial_id)
        if action in ['approved', 'rejected']:
            testimonial.status = action
            testimonial.save()
    pending = Testimonial.objects.filter(status='pending').order_by('-created_at')
    approved = Testimonial.objects.filter(status='approved').order_by('-created_at')
    return render(request, 'accounts/manage_testimonials.html', {'pending': pending, 'approved': approved})
