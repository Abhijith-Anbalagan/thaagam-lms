from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Avg, Count, Q
from accounts.decorators import role_required
from accounts.models import User, Invitation


@role_required('management')
def dashboard(request):
    school     = request.user.school
    my_invites = request.user.sent_invites.filter(role='teacher', accepted=True).values_list('email', flat=True)

    from classrooms.models import Classroom
    from assignments.models import Assignment, Submission
    from announcements.models import Announcement

    teachers   = User.objects.filter(email__in=my_invites, role='teacher')
    classrooms = Classroom.objects.filter(school=school, teacher__in=teachers)

    # ── Post announcement ──
    if request.method == 'POST' and request.POST.get('action') == 'announce':
        title     = request.POST.get('title', '').strip()
        body      = request.POST.get('body', '').strip()
        target    = request.POST.get('target', 'all')
        is_pinned = bool(request.POST.get('is_pinned'))
        if title and body:
            Announcement.objects.create(
                posted_by=request.user, school=school,
                title=title, body=body, target=target, is_pinned=is_pinned,
            )
            messages.success(request, 'Announcement posted.')
            return redirect('management_dashboard')

    # ── Teacher tab stats ──
    total_assignments = Assignment.objects.filter(classroom__in=classrooms).count()
    total_videos      = sum(
        c.course_contents.filter(content_type='video').count() for c in classrooms
    )

    teacher_data = []
    for t in teachers:
        t_classes     = classrooms.filter(teacher=t)
        assignments_n = Assignment.objects.filter(classroom__in=t_classes).count()
        videos_n      = sum(c.course_contents.filter(content_type='video').count() for c in t_classes)
        teacher_data.append({
            'name':        t.get_full_name() or t.username,
            'classes':     t_classes.count(),
            'assignments': assignments_n,
            'videos':      videos_n,
            'students':    sum(c.student_count for c in t_classes),
        })

    # ── Classroom tab stats ──
    total_course_content  = sum(c.course_contents.count() for c in classrooms)
    total_announcements   = Announcement.objects.filter(school=school).count()

    # ── Student tab stats ──
    total_students = User.objects.filter(school=school, role='student').count()

    total_submissions = Submission.objects.filter(assignment__classroom__in=classrooms).count()
    total_possible    = sum(c.assignments.count() * c.student_count for c in classrooms)
    avg_submission_rate = round(total_submissions / total_possible * 100, 1) if total_possible else 0

    avg_grade_val = Submission.objects.filter(
        assignment__classroom__in=classrooms, score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']
    avg_grade = round(avg_grade_val, 1) if avg_grade_val else 0

    # Attendance mock (replace with real attendance model when available)
    # attendance_rate removed

    # ── Per-classroom breakdown (used in Students + Classrooms tabs) ──
    class_perf = []
    for c in classrooms:
        total_s = c.assignments.count() * c.student_count
        subs    = Submission.objects.filter(assignment__classroom=c).count()
        avg_s   = Submission.objects.filter(
            assignment__classroom=c, score__isnull=False
        ).aggregate(avg=Avg('score'))['avg']
        class_perf.append({
            'name':            c.name,
            'teacher':         c.teacher.get_full_name() or c.teacher.username,
            'students':        c.student_count,
            'announcements':   c.announcements.count(),
            'content':         c.course_contents.count(),
            'assignments':     c.assignments.count(),
            'submission_rate': round(subs / total_s * 100, 1) if total_s else 0,
            'avg_grade':       round(avg_s, 1) if avg_s else 0,
        })

    # ── Deadline tracker (Teachers tab) ──
    from django.utils import timezone
    now = timezone.now()
    deadline_tracker = []
    for a in Assignment.objects.filter(classroom__in=classrooms).select_related('classroom', 'classroom__teacher').order_by('due_date'):
        total_students = a.classroom.student_count
        submitted      = a.submissions.count()
        days_remaining = (a.due_date - now).days
        rate           = round(submitted / total_students * 100) if total_students else 0
        if now > a.due_date:
            status = 'overdue'
        elif rate == 100:
            status = 'on_time'
        else:
            status = 'in_progress'
        deadline_tracker.append({
            'title':           a.title,
            'classroom':       a.classroom.name,
            'teacher':         a.classroom.teacher.get_full_name() or a.classroom.teacher.username,
            'assigned_date':   a.created_at,
            'due_date':        a.due_date,
            'days_remaining':  days_remaining,
            'submitted':       submitted,
            'total_students':  total_students,
            'rate':            rate,
            'status':          status,
        })

    # ── Analytics tab ──
    from analytics.services.analytics_services import ManagementAnalyticsService
    svc = ManagementAnalyticsService(request.user)

    course_completion   = list(svc.get_course_completion_rates())
    assignment_analytics = list(svc.get_assignment_submission_analytics())
    engagement          = svc.get_engagement_metrics()
    dept_performance    = list(svc.get_department_performance())

    # top/bottom performers
    top_classrooms  = sorted(dept_performance, key=lambda x: x['avg_score'] or 0, reverse=True)[:3]
    weak_classrooms = sorted(dept_performance, key=lambda x: x['avg_score'] or 0)[:3]

    # assignment summary
    total_assign_count = len(assignment_analytics)
    avg_submit_rate    = round(
        sum(a['submission_rate'] or 0 for a in assignment_analytics) / total_assign_count, 1
    ) if total_assign_count else 0

    # ── Analytics tab — weekly progress mock ──
    weekly_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6']
    weekly_scores = [52, 58, 63, 70, 74, 79]

    # ── Announcements tab ──
    ann_teachers = Announcement.objects.filter(school=school, target='teachers').order_by('-created_at')[:10]
    ann_students = Announcement.objects.filter(school=school, target='students').order_by('-created_at')[:10]
    ann_pinned   = Announcement.objects.filter(school=school, is_pinned=True).order_by('-created_at')[:10]

    # Combined recent announcements for dashboard
    recent_announcements = Announcement.objects.filter(school=school).order_by('-created_at')[:3]
    total_announcements = Announcement.objects.filter(school=school).count()

    return render(request, 'management/dashboard.html', {
        # teachers tab
        'teachers':           teachers,
        'teacher_data':       teacher_data,
        'total_teachers':     teachers.count(),
        'total_classrooms':   classrooms.count(),
        'total_assignments':  total_assignments,
        'total_videos':       total_videos,
        'deadline_tracker':   deadline_tracker,
        # classrooms tab
        'class_perf':         class_perf,
        'total_course_content': total_course_content,
        'total_announcements':  total_announcements,
        # students tab
        'total_students':       total_students,
        'avg_submission_rate':  avg_submission_rate,
        'avg_grade':            avg_grade,
        # analytics tab
        'course_completion':     course_completion,
        'assignment_analytics':  assignment_analytics,
        'engagement':            engagement,
        'dept_performance':      dept_performance,
        'top_classrooms':        top_classrooms,
        'weak_classrooms':       weak_classrooms,
        'avg_submit_rate':       avg_submit_rate,
        'total_assign_count':    total_assign_count,
        # weekly
        'weekly_labels':         weekly_labels,
        'weekly_scores':         weekly_scores,
        # announcements tab
        'ann_teachers':         ann_teachers,
        'ann_students':         ann_students,
        'ann_pinned':           ann_pinned,
        'recent_announcements': recent_announcements,
        'total_announcements':  total_announcements,
    })


@role_required('management')
def invite_teacher(request):
    from django.conf import settings
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    school     = request.user.school
    invited_by = request.user.get_full_name() or request.user.username
    site_url   = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

    # ── Single invite ──
    if request.method == 'POST' and not request.FILES.get('file'):
        email = request.POST.get('email', '').strip()
        role  = request.POST.get('role', 'teacher')
        if role not in ('teacher', 'student'):
            role = 'teacher'
        if email:
            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, f'{email} is already a registered user.')
            elif Invitation.objects.filter(email__iexact=email, accepted=False, school=school).exists():
                messages.error(request, f'An invitation has already been sent to {email}.')
            else:
                inv = Invitation.objects.create(
                    email=email, role=role, school=school, invited_by=request.user,
                )
                activate_url = f'{site_url}/accept-invite/{inv.token}/'
                html_body = render_to_string('school_admin/email_invite.html', {
                    'email': email, 'school_name': school.name,
                    'invited_by': invited_by, 'activate_url': activate_url, 'role': role,
                })
                send_mail(
                    subject=f"You're invited to join {school.name} on EduPlatform",
                    message=f'You have been invited as {role.title()}. Accept: {activate_url}',
                    from_email=None, recipient_list=[email],
                    html_message=html_body, fail_silently=True,
                )
                messages.success(request, f'Invitation sent to {email} as {role.title()}.')
        return redirect('management_invite_teacher')

    # ── Bulk invite via CSV/Excel ──
    if request.method == 'POST' and request.FILES.get('file'):
        from django.http import JsonResponse
        uploaded = request.FILES['file']
        role     = request.POST.get('bulk_role', 'teacher')
        if role not in ('teacher', 'student'):
            role = 'teacher'
        filename = uploaded.name.lower()
        emails   = []
        try:
            if filename.endswith('.csv'):
                import csv, io
                text = uploaded.read().decode('utf-8-sig')
                for row in csv.reader(io.StringIO(text)):
                    for cell in row:
                        val = cell.strip()
                        if '@' in val:
                            emails.append(val.lower())
            elif filename.endswith(('.xlsx', '.xls')):
                import openpyxl
                wb = openpyxl.load_workbook(uploaded, read_only=True, data_only=True)
                for row in wb.active.iter_rows(values_only=True):
                    for cell in row:
                        if cell and isinstance(cell, str) and '@' in cell:
                            emails.append(cell.strip().lower())
                wb.close()
            else:
                return JsonResponse({'error': 'Only .csv, .xlsx or .xls files are supported.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Could not read file: {str(e)}'}, status=400)

        emails = list(dict.fromkeys(emails))
        if not emails:
            return JsonResponse({'error': 'No email addresses found in the file.'}, status=400)

        sent, failed = [], []
        for email in emails:
            if len(email) > 254 or '.' not in email.split('@')[-1]:
                failed.append({'email': email, 'reason': 'Invalid email format'}); continue
            if User.objects.filter(email__iexact=email).exists():
                failed.append({'email': email, 'reason': 'Already a registered user'}); continue
            if Invitation.objects.filter(email__iexact=email, accepted=False, school=school).exists():
                failed.append({'email': email, 'reason': 'Invite already sent'}); continue
            try:
                inv = Invitation.objects.create(
                    email=email, role=role, school=school, invited_by=request.user,
                )
                activate_url = f'{site_url}/accept-invite/{inv.token}/'
                html_body = render_to_string('school_admin/email_invite.html', {
                    'email': email, 'school_name': school.name,
                    'invited_by': invited_by, 'activate_url': activate_url, 'role': role,
                })
                send_mail(
                    subject=f"You're invited to join {school.name} on EduPlatform",
                    message=f'You have been invited as {role.title()}. Accept: {activate_url}',
                    from_email=None, recipient_list=[email],
                    html_message=html_body, fail_silently=True,
                )
                sent.append(email)
            except Exception as e:
                failed.append({'email': email, 'reason': str(e)})

        return JsonResponse({
            'success': True, 'total': len(emails),
            'sent': len(sent), 'failed': len(failed),
            'sent_list': sent, 'failed_list': failed,
        })

    pending_invites = Invitation.objects.filter(
        school=school, invited_by=request.user,
        role__in=['teacher', 'student'], accepted=False,
    ).order_by('-created_at')
    return render(request, 'management/invite_teacher.html', {
        'pending_invites': pending_invites,
    })


@role_required('management')
def teachers_list(request):
    my_invites = request.user.sent_invites.filter(role='teacher', accepted=True).values_list('email', flat=True)
    teachers   = User.objects.filter(email__in=my_invites, role='teacher')
    return render(request, 'management/teachers_list.html', {'teachers': teachers})


@role_required('management')
def announcements_management(request):
    from announcements.models import Announcement
    from django.db.models import Q
    
    school = request.user.school
    
    # ── Handle POST requests for creating announcement ──
    if request.method == 'POST' and request.POST.get('action') == 'create':
        title     = request.POST.get('title', '').strip()
        body      = request.POST.get('body', '').strip()
        target    = request.POST.get('target', 'all')
        is_pinned = bool(request.POST.get('is_pinned'))
        meet_link = request.POST.get('meet_link', '').strip()
        
        if title and body:
            Announcement.objects.create(
                posted_by=request.user,
                school=school,
                title=title,
                body=body,
                target=target,
                is_pinned=is_pinned,
                meet_link=meet_link if meet_link else '',
            )
            messages.success(request, 'Announcement created successfully.')
            return redirect('management_announcements')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    # ── Handle DELETE requests ──
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        announcement_id = request.POST.get('announcement_id')
        try:
            announcement = Announcement.objects.get(id=announcement_id, school=school)
            announcement.delete()
            messages.success(request, 'Announcement deleted successfully.')
        except Announcement.DoesNotExist:
            messages.error(request, 'Announcement not found.')
        return redirect('management_announcements')
    
    # ── Announcement counts for summary page ──
    all_announcements = Announcement.objects.filter(school=school).select_related('posted_by')
    sent_announcements = all_announcements.filter(posted_by__role='management')
    from_announcements = all_announcements.exclude(posted_by__role='management')

    return render(request, 'management/announcements.html', {
        'sent_count': sent_announcements.count(),
        'from_count': from_announcements.count(),
    })


@role_required('management')
def announcements_detail(request, mode):
    from announcements.models import Announcement

    school = request.user.school

    if request.method == 'POST' and request.POST.get('action') == 'delete':
        announcement_id = request.POST.get('announcement_id')
        try:
            announcement = Announcement.objects.get(id=announcement_id, school=school)
            announcement.delete()
            messages.success(request, 'Announcement deleted successfully.')
        except Announcement.DoesNotExist:
            messages.error(request, 'Announcement not found.')
        return redirect('management_announcements_detail', mode=mode)

    all_announcements = Announcement.objects.filter(school=school).select_related('posted_by').order_by('-is_pinned', '-created_at')
    if mode == 'sent':
        announcements = all_announcements.filter(posted_by__role='management')
        title = 'Sent Announcements'
        subtitle = 'Announcements posted by management.'
    elif mode == 'from':
        announcements = all_announcements.exclude(posted_by__role='management')
        title = 'Announcements from Others'
        subtitle = 'Announcements posted by other roles.'
    else:
        return redirect('management_announcements')

    return render(request, 'management/announcements_detail.html', {
        'announcements': announcements,
        'mode': mode,
        'title': title,
        'subtitle': subtitle,
    })
