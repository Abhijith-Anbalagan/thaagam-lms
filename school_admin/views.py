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
    pending       = Invitation.objects.filter(school=school, accepted=False).order_by('-created_at')
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
        role  = request.POST.get('role', 'management')
        if role not in ('management', 'teacher'):
            role = 'management'
        if email:
            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, f'{email} is already a registered user.')
                return redirect('school_admin_invite_management')
            if Invitation.objects.filter(email__iexact=email, accepted=False).exists():
                messages.error(request, f'An invitation has already been sent to {email}.')
                return redirect('school_admin_invite_management')
            inv = Invitation.objects.create(
                email=email, role=role,
                school=request.user.school, invited_by=request.user,
            )
            from django.conf import settings
            from django.core.mail import send_mail
            site_url     = settings.SITE_URL.rstrip('/')
            activate_url = f'{site_url}/accept-invite/{inv.token}/'
            html_body = render_to_string('school_admin/email_invite.html', {
                'email':        email,
                'school_name':  request.user.school.name,
                'invited_by':   request.user.get_full_name() or request.user.username,
                'activate_url': activate_url,
                'role':         role,
            })
            send_mail(
                subject=f"You're invited to join {request.user.school.name} on EduPlatform",
                message=f'You have been invited as {role.title()}. Accept: {activate_url}',
                from_email=None,
                recipient_list=[email],
                html_message=html_body,
                fail_silently=True,
            )
            messages.success(request, f'Invitation sent to {email} as {role.title()}.')
            return redirect('school_admin_invite_management')
    return render(request, 'school_admin/invite_management.html')


@role_required('school_admin')
def bulk_invite(request):
    """Parse CSV/Excel file and send invitations to all valid emails."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    uploaded = request.FILES.get('file')
    role     = request.POST.get('role', 'management')
    if role not in ('management', 'teacher'):
        role = 'management'

    if not uploaded:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    filename = uploaded.name.lower()
    emails   = []

    try:
        if filename.endswith('.csv'):
            import csv, io
            text = uploaded.read().decode('utf-8-sig')  # handle BOM
            reader = csv.reader(io.StringIO(text))
            for row in reader:
                for cell in row:
                    val = cell.strip()
                    if '@' in val:
                        emails.append(val.lower())

        elif filename.endswith(('.xlsx', '.xls')):
            import openpyxl
            wb = openpyxl.load_workbook(uploaded, read_only=True, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if cell and isinstance(cell, str) and '@' in cell:
                        emails.append(cell.strip().lower())
            wb.close()
        else:
            return JsonResponse({'error': 'Only .csv, .xlsx or .xls files are supported.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Could not read file: {str(e)}'}, status=400)

    if not emails:
        return JsonResponse({'error': 'No email addresses found in the file.'}, status=400)

    # Deduplicate
    emails = list(dict.fromkeys(emails))

    from django.conf import settings
    from django.core.mail import send_mail

    school      = request.user.school
    invited_by  = request.user.get_full_name() or request.user.username
    site_url    = settings.SITE_URL.rstrip('/')

    sent = []
    failed = []

    for email in emails:
        # Validate basic format
        if len(email) > 254 or '.' not in email.split('@')[-1]:
            failed.append({'email': email, 'reason': 'Invalid email format'})
            continue

        if User.objects.filter(email__iexact=email).exists():
            failed.append({'email': email, 'reason': 'Already a registered user'})
            continue

        if Invitation.objects.filter(email__iexact=email, accepted=False, school=school).exists():
            failed.append({'email': email, 'reason': 'Invite already sent'})
            continue

        try:
            inv = Invitation.objects.create(
                email=email, role=role,
                school=school, invited_by=request.user,
            )
            activate_url = f'{site_url}/accept-invite/{inv.token}/'
            html_body = render_to_string('school_admin/email_invite.html', {
                'email':        email,
                'school_name':  school.name,
                'invited_by':   invited_by,
                'activate_url': activate_url,
                'role':         role,
            })
            send_mail(
                subject=f"You're invited to join {school.name} on EduPlatform",
                message=f'You have been invited as {role.title()}. Accept: {activate_url}',
                from_email=None,
                recipient_list=[email],
                html_message=html_body,
                fail_silently=True,
            )
            sent.append(email)
        except Exception as e:
            failed.append({'email': email, 'reason': str(e)})

    return JsonResponse({
        'success': True,
        'total':   len(emails),
        'sent':    len(sent),
        'failed':  len(failed),
        'sent_list':   sent,
        'failed_list': failed,
    })


@role_required('school_admin')
def activate_invite(request, invite_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    school = request.user.school
    inv    = get_object_or_404(Invitation, id=invite_id, school=school)
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
    user = User(username=username, email=inv.email, role=inv.role, school=school)
    user.set_password(temp_password)
    user.save()
    inv.accepted = True
    inv.save()
    from django.core.mail import send_mail
    send_mail(
        subject=f'Your EduPlatform {inv.role.title()} Account is Active',
        message=f'Your account has been activated.\nEmail: {inv.email}\nTemporary Password: {temp_password}\nLogin: /login/',
        from_email=None,
        recipient_list=[inv.email],
        fail_silently=True,
    )
    return JsonResponse({
        'success': True,
        'user': {
            'id':    user.id,
            'name':  user.get_full_name() or user.username,
            'email': user.email,
        }
    })


@role_required('school_admin')
def delete_invite(request, invite_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    school = request.user.school
    inv    = get_object_or_404(Invitation, id=invite_id, school=school, accepted=False)
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
def management_detail(request, user_id):
    school = request.user.school
    member = get_object_or_404(User, id=user_id, school=school, role='management')
    return render(request, 'school_admin/management_detail.html', {'member': member})


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
    from classrooms.models import Classroom
    school     = request.user.school
    classrooms = Classroom.objects.filter(school=school).annotate(
        num_students=Count('students', distinct=True),
        assignment_count=Count('assignments', distinct=True),
        submission_count=Count('assignments__submissions', distinct=True),
        avg_score=Avg('assignments__submissions__score'),
    )
    teachers   = User.objects.filter(school=school, role='teacher')
    students   = User.objects.filter(school=school, role='student')
    avg_score  = Submission.objects.filter(
        assignment__classroom__school=school, score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']
    total_submissions = Submission.objects.filter(
        assignment__classroom__school=school
    ).count()
    graded_submissions = Submission.objects.filter(
        assignment__classroom__school=school, score__isnull=False
    ).count()
    return render(request, 'school_admin/reports.html', {
        'school':              school,
        'classrooms':          classrooms,
        'avg_score':           avg_score,
        'total_teachers':      teachers.count(),
        'total_students':      students.count(),
        'total_submissions':   total_submissions,
        'graded_submissions':  graded_submissions,
    })


@role_required('school_admin')
def teachers_list(request):
    school   = request.user.school
    teachers = User.objects.filter(school=school, role='teacher').annotate(
        classroom_count=Count('classrooms'),
        num_students=Count('classrooms__students', distinct=True),
        submission_count=Count('classrooms__assignments__submissions', distinct=True),
    ).prefetch_related('classrooms').order_by('first_name')
    total_classrooms = Classroom.objects.filter(school=school).count()
    active_teachers  = teachers.filter(is_active=True).count()
    return render(request, 'school_admin/teachers_list.html', {
        'teachers':         teachers,
        'school':           school,
        'total_classrooms': total_classrooms,
        'active_teachers':  active_teachers,
    })


@role_required('school_admin')
def students_list(request):
    school   = request.user.school
    students = User.objects.filter(school=school, role='student').annotate(
        submission_count=Count('submissions'),
        avg_score=Avg('submissions__score'),
        classroom_count=Count('joined_classrooms', distinct=True),
    ).order_by('first_name')

    # Chart data
    score_ranges = {'s90_100': 0, 's75_89': 0, 's50_74': 0, 's0_49': 0, 'no_score': 0}
    for s in students:
        if s.avg_score is None:
            score_ranges['no_score'] += 1
        elif s.avg_score >= 90:
            score_ranges['s90_100'] += 1
        elif s.avg_score >= 75:
            score_ranges['s75_89'] += 1
        elif s.avg_score >= 50:
            score_ranges['s50_74'] += 1
        else:
            score_ranges['s0_49'] += 1

    return render(request, 'school_admin/students_list.html', {
        'students': students,
        'school': school,
        'score_ranges': score_ranges,
        'total_students': students.count(),
    })


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