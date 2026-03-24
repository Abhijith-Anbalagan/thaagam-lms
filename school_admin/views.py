from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.template.loader import render_to_string
from accounts.decorators import role_required
from accounts.models import User, Invitation


@role_required('school_admin')
def dashboard(request):
    school      = request.user.school
    teachers    = User.objects.filter(school=school, role='teacher')
    students    = User.objects.filter(school=school, role='student')
    management  = User.objects.filter(school=school, role='management')
    pending     = Invitation.objects.filter(school=school, role='management', accepted=False).order_by('-created_at')
    from classrooms.models import Classroom
    from announcements.models import Announcement
    classrooms  = Classroom.objects.filter(school=school)
    announcements = Announcement.objects.filter(school=school).order_by('-created_at')[:5]
    return render(request, 'school_admin/dashboard.html', {
        'school': school, 'teachers': teachers, 'students': students,
        'management': management, 'classrooms': classrooms,
        'announcements': announcements, 'pending_invites': pending,
        'total_teachers': teachers.count(), 'total_students': students.count(),
        'total_classrooms': classrooms.count(),
    })


@role_required('school_admin')
def invite_management(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            inv = Invitation.objects.create(
                email=email, role='management',
                school=request.user.school, invited_by=request.user,
            )
            from django.conf import settings
            site_url     = settings.SITE_URL.rstrip('/')
            activate_url = f'{site_url}/accept-invite/{inv.token}/'
            html_body = render_to_string('school_admin/email_invite.html', {
                'email':        email,
                'school_name':  request.user.school.name,
                'invited_by':   request.user.get_full_name() or request.user.username,
                'activate_url': activate_url,
            })
            from django.core.mail import send_mail
            send_mail(
                subject=f'You\'re invited to join {request.user.school.name} on EduPlatform',
                message=f'You have been invited as Management. Accept: {activate_url}',
                from_email=None,
                recipient_list=[email],
                html_message=html_body,
                fail_silently=True,
            )
            messages.success(request, f'Invitation sent to {email}.')
            return redirect('school_admin_dashboard')
    return render(request, 'school_admin/invite_management.html')


@role_required('school_admin')
def activate_invite(request, invite_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    school = request.user.school
    inv    = get_object_or_404(Invitation, id=invite_id, school=school, role='management')
    if inv.accepted:
        return JsonResponse({'error': 'Already accepted'}, status=400)
    if timezone.now() > inv.expires_at:
        return JsonResponse({'error': 'Invitation expired'}, status=400)
    base = inv.email.split('@')[0]; username = base; i = 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{i}'; i += 1
    import secrets, string
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    user = User(username=username, email=inv.email, role='management', school=school)
    user.set_password(temp_password)
    user.save()
    inv.accepted = True
    inv.save()
    from django.core.mail import send_mail
    send_mail(
        subject='Your EduPlatform Management Account is Active',
        message=f'Your account has been activated.\nEmail: {inv.email}\nTemporary Password: {temp_password}\nLogin: /login/',
        from_email=None,
        recipient_list=[inv.email],
        fail_silently=True,
    )
    return JsonResponse({
        'success': True,
        'user': {
            'id':       user.id,
            'name':     user.get_full_name() or user.username,
            'email':    user.email,
            'username': user.username,
        }
    })


@role_required('school_admin')
def delete_invite(request, invite_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    school = request.user.school
    inv    = get_object_or_404(Invitation, id=invite_id, school=school, role='management', accepted=False)
    inv.delete()
    return JsonResponse({'success': True})


@role_required('school_admin')
def delete_management(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    school = request.user.school
    user   = get_object_or_404(User, id=user_id, school=school, role='management')
    user.delete()
    return JsonResponse({'success': True})


@role_required('school_admin')
def management_list(request):
    school     = request.user.school
    management = User.objects.filter(school=school, role='management')
    return render(request, 'school_admin/management_list.html', {'management': management})


@role_required('school_admin')
def reports(request):
    school = request.user.school
    from classrooms.models import Classroom
    from assignments.models import Submission
    from django.db.models import Avg
    classrooms = Classroom.objects.filter(school=school)
    avg_score  = Submission.objects.filter(
        assignment__classroom__school=school, score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']
    return render(request, 'school_admin/reports.html', {
        'school': school, 'classrooms': classrooms, 'avg_score': avg_score,
    })
