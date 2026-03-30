from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import Count, Avg
from accounts.decorators import role_required
from accounts.models import User, Invitation
from classrooms.models import Classroom
from assignments.models import Submission


@role_required('school_admin')
def dashboard(request):
    from announcements.models import Announcement
    from datetime import date
    school        = request.user.school
    teachers      = User.objects.filter(school=school, role='teacher')
    students      = User.objects.filter(school=school, role='student')
    management    = User.objects.filter(school=school, role='management')
    pending       = Invitation.objects.filter(school=school, role='management', accepted=False).order_by('-created_at')
    classrooms    = Classroom.objects.filter(school=school)
    announcements = Announcement.objects.filter(school=school).order_by('-created_at')[:5]
    return render(request, 'school_admin/dashboard.html', {
        'school': school,
        'teachers': teachers,
        'students': students,
        'management': management,
        'classrooms': classrooms,
        'announcements': announcements,
        'pending_invites': pending,
        'total_teachers': teachers.count(),
        'total_students': students.count(),
        'total_classrooms': classrooms.count(),
        'total_management': management.count(),
        'today': date.today(),
    })


@role_required('school_admin')
def invite_management(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            # Check if user already exists
            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, f'{email} is already a registered user.')
                return redirect('school_admin_invite_management')

            # Check if a pending invite already exists
            if Invitation.objects.filter(email__iexact=email, accepted=False).exists():
                messages.error(request, f'An invitation has already been sent to {email}.')
                return redirect('school_admin_invite_management')

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
                subject=f"You're invited to join {request.user.school.name} on EduPlatform",
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
    base = inv.email.split('@')[0]
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{i}'
        i += 1
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
    management = User.objects.filter(school=school, role='management').annotate(
        invite_count=Count('sent_invites')
    )
    return render(request, 'school_admin/management_list.html', {'management': management})


@role_required('school_admin')
def poll_management(request):
    school     = request.user.school
    management = User.objects.filter(school=school, role='management').values(
        'id', 'first_name', 'last_name', 'username', 'email'
    )
    pending = Invitation.objects.filter(
        school=school, role='management', accepted=False
    ).order_by('-created_at').values('id', 'email', 'created_at', 'expires_at')

    def fmt_user(u):
        full = f"{u['first_name']} {u['last_name']}".strip() or u['username']
        return {'id': u['id'], 'name': full, 'email': u['email']}

    def fmt_inv(i):
        created_local = timezone.localtime(i['created_at'])
        expires_local = timezone.localtime(i['expires_at'])
        created = created_local.strftime('%b %d, %Y')
        expires = expires_local.strftime('%b %d')
        expired = timezone.now() > i['expires_at']
        return {
            'id': i['id'], 'email': i['email'],
            'created': created, 'expires': expires, 'expired': expired,
        }

    return JsonResponse({
        'management': [fmt_user(u) for u in management],
        'pending':    [fmt_inv(i) for i in pending],
    })


@role_required('school_admin')
def reports(request):
    school     = request.user.school
    classrooms = Classroom.objects.filter(school=school)
    teachers   = User.objects.filter(school=school, role='teacher')
    students   = User.objects.filter(school=school, role='student')
    avg_score  = Submission.objects.filter(
        assignment__classroom__school=school, score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']
    return render(request, 'school_admin/reports.html', {
        'school': school,
        'classrooms': classrooms,
        'avg_score': avg_score,
        'total_teachers': teachers.count(),
        'total_students': students.count(),
    })


@role_required('school_admin')
def teachers_list(request):
    school   = request.user.school
    teachers = User.objects.filter(school=school, role='teacher').annotate(
        classroom_count=Count('classrooms')
    )
    return render(request, 'school_admin/teachers_list.html', {'teachers': teachers})


@role_required('school_admin')
def students_list(request):
    school   = request.user.school
    students = User.objects.filter(school=school, role='student').annotate(
        submission_count=Count('submissions'),
        avg_score=Avg('submissions__score')
    )
    return render(request, 'school_admin/students_list.html', {'students': students})


@role_required('school_admin')
def create_announcement(request):
    from announcements.models import Announcement
    if request.method == 'POST':
        title  = request.POST.get('title', '').strip()
        body   = request.POST.get('body', '').strip()
        pinned = request.POST.get('is_pinned') == 'on'
        if title and body:
            Announcement.objects.create(
                title=title,
                body=body,
                school=request.user.school,
                posted_by=request.user,
                is_pinned=pinned,
            )
            messages.success(request, 'Announcement posted successfully.')
            return redirect('school_admin_dashboard')
        else:
            messages.error(request, 'Title and body are required.')
    return render(request, 'school_admin/create_announcement.html')