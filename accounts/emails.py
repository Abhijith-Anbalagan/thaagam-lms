from django.core.mail import send_mail
from django.conf import settings


def send_verification_email(user, verification_url):
    subject = 'Verify your EduPlatform email'

    # Plain text fallback
    plain = (
        f'Hi {user.username},\n\n'
        f'Click the link below to verify your email:\n{verification_url}\n\n'
        f'This link expires in 24 hours.\n\n'
        f'If you did not create an account, you can safely ignore this email.'
    )

    # HTML version
    html = f'''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f7f6f2;font-family:'Segoe UI',Arial,sans-serif;">

  <div style="max-width:560px;margin:40px auto;background:#ffffff;border-radius:10px;overflow:hidden;border:1px solid #e8e6e0;box-shadow:0 4px 16px rgba(0,0,0,.08);">

    <!-- Header -->
    <div style="background:#1a1f36;padding:28px 36px;">
      <span style="color:#4c68d7;font-size:20px;font-weight:700;letter-spacing:-0.5px;">EduPlatform</span>
    </div>

    <!-- Body -->
    <div style="padding:36px;">
      <h2 style="margin:0 0 8px;font-size:22px;color:#1a1f36;font-weight:700;">Verify your email address</h2>
      <p style="margin:0 0 24px;color:#9e9c95;font-size:15px;">
        Hi <strong style="color:#3d3d3a;">{user.username}</strong>, thanks for signing up!
      </p>

      <p style="margin:0 0 24px;color:#3d3d3a;font-size:15px;line-height:1.6;">
        Click the button below to verify your email address and activate your EduPlatform account.
      </p>

      <!-- Button -->
      <div style="text-align:center;margin:32px 0;">
        <a href="{verification_url}"
           style="background:#4c68d7;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:6px;font-size:15px;font-weight:600;display:inline-block;letter-spacing:-0.2px;">
          Verify Email Address
        </a>
      </div>

      <!-- Fallback link -->
      <p style="margin:24px 0 0;font-size:13px;color:#9e9c95;line-height:1.6;">
        Button not working? Copy and paste this link into your browser:<br>
        <a href="{verification_url}" style="color:#4c68d7;word-break:break-all;font-size:12px;">{verification_url}</a>
      </p>

      <hr style="border:none;border-top:1px solid #e8e6e0;margin:28px 0;">

      <!-- Warning -->
      <div style="background:#f7f6f2;border-radius:6px;padding:14px 16px;">
        <p style="margin:0;font-size:13px;color:#9e9c95;line-height:1.6;">
          ⏱ This link expires in <strong style="color:#3d3d3a;">24 hours</strong>.<br>
          If you didn't create an account on EduPlatform, you can safely ignore this email.
        </p>
      </div>
    </div>

    <!-- Footer -->
    <div style="background:#f7f6f2;padding:20px 36px;border-top:1px solid #e8e6e0;">
      <p style="margin:0;font-size:12px;color:#9e9c95;">
        © EduPlatform &nbsp;·&nbsp; You're receiving this because you signed up at EduPlatform.
      </p>
    </div>

  </div>

</body>
</html>
    '''

    send_mail(
        subject,
        plain,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html,
        fail_silently=False,
    )


def send_password_reset_email(user, reset_url):
    subject = 'Reset your EduPlatform password'

    # Plain text fallback
    plain = (
        f'Hi {user.username},\n\n'
        f'Click the link below to reset your password:\n{reset_url}\n\n'
        f'This link expires in 2 hours.\n\n'
        f'If you did not request a password reset, you can safely ignore this email.'
    )

    # HTML version
    html = f'''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f7f6f2;font-family:'Segoe UI',Arial,sans-serif;">

  <div style="max-width:560px;margin:40px auto;background:#ffffff;border-radius:10px;overflow:hidden;border:1px solid #e8e6e0;box-shadow:0 4px 16px rgba(0,0,0,.08);">

    <!-- Header -->
    <div style="background:#1a1f36;padding:28px 36px;">
      <span style="color:#4c68d7;font-size:20px;font-weight:700;letter-spacing:-0.5px;">EduPlatform</span>
    </div>

    <!-- Body -->
    <div style="padding:36px;">
      <h2 style="margin:0 0 8px;font-size:22px;color:#1a1f36;font-weight:700;">Reset your password</h2>
      <p style="margin:0 0 24px;color:#9e9c95;font-size:15px;">
        Hi <strong style="color:#3d3d3a;">{user.username}</strong>
      </p>

      <p style="margin:0 0 24px;color:#3d3d3a;font-size:15px;line-height:1.6;">
        We received a request to reset your EduPlatform password. Click the button below to choose a new one.
      </p>

      <!-- Button -->
      <div style="text-align:center;margin:32px 0;">
        <a href="{reset_url}"
           style="background:#4c68d7;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:6px;font-size:15px;font-weight:600;display:inline-block;letter-spacing:-0.2px;">
          Reset Password
        </a>
      </div>

      <!-- Fallback link -->
      <p style="margin:24px 0 0;font-size:13px;color:#9e9c95;line-height:1.6;">
        Button not working? Copy and paste this link into your browser:<br>
        <a href="{reset_url}" style="color:#4c68d7;word-break:break-all;font-size:12px;">{reset_url}</a>
      </p>

      <hr style="border:none;border-top:1px solid #e8e6e0;margin:28px 0;">

      <!-- Warning -->
      <div style="background:#f7f6f2;border-radius:6px;padding:14px 16px;">
        <p style="margin:0;font-size:13px;color:#9e9c95;line-height:1.6;">
          ⏱ This link expires in <strong style="color:#3d3d3a;">2 hours</strong>.<br>
          If you didn't request a password reset, you can safely ignore this email — your password will not be changed.
        </p>
      </div>
    </div>

    <!-- Footer -->
    <div style="background:#f7f6f2;padding:20px 36px;border-top:1px solid #e8e6e0;">
      <p style="margin:0;font-size:12px;color:#9e9c95;">
        © EduPlatform &nbsp;·&nbsp; You're receiving this because a reset was requested for your account.
      </p>
    </div>

  </div>

</body>
</html>
    '''

    send_mail(
        subject,
        plain,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html,
        fail_silently=False,
    )