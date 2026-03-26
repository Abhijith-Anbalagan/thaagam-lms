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
    attendance_rate = 85

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
            'attendance':      attendance_rate,   # mock per class
        })

    # ── Analytics tab — weekly progress mock ──
    weekly_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6']
    weekly_scores = [52, 58, 63, 70, 74, 79]

    # ── Announcements tab ──
    ann_teachers = Announcement.objects.filter(school=school, target='teachers').order_by('-created_at')[:10]
    ann_students = Announcement.objects.filter(school=school, target='students').order_by('-created_at')[:10]
    ann_pinned   = Announcement.objects.filter(school=school, is_pinned=True).order_by('-created_at')[:10]

    return render(request, 'management/dashboard.html', {
        # teachers tab
        'teachers':           teachers,
        'teacher_data':       teacher_data,
        'total_teachers':     teachers.count(),
        'total_classrooms':   classrooms.count(),
        'total_assignments':  total_assignments,
        'total_videos':       total_videos,
        # classrooms tab
        'class_perf':         class_perf,
        'total_course_content': total_course_content,
        'total_announcements':  total_announcements,
        # students tab
        'total_students':       total_students,
        'avg_submission_rate':  avg_submission_rate,
        'avg_grade':            avg_grade,
        'attendance_rate':      attendance_rate,
        # analytics tab
        'weekly_labels':        weekly_labels,
        'weekly_scores':        weekly_scores,
        # announcements tab
        'ann_teachers':         ann_teachers,
        'ann_students':         ann_students,
        'ann_pinned':           ann_pinned,
    })


@role_required('management')
def invite_teacher(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            inv = Invitation.objects.create(
                email=email, role='teacher',
                school=request.user.school, invited_by=request.user,
            )
            url = request.build_absolute_uri(f'/accept-invite/{inv.token}/')
            from django.core.mail import send_mail
            send_mail('EduPlatform Teacher Invitation',
                      f'You are invited as a Teacher.\nAccept: {url}',
                      'noreply@eduplatform.com', [email], fail_silently=True)
            messages.success(request, f'Invitation sent to {email}.')
            return redirect('management_dashboard')
    return render(request, 'management/invite_teacher.html')


@role_required('management')
def teachers_list(request):
    my_invites = request.user.sent_invites.filter(role='teacher', accepted=True).values_list('email', flat=True)
    teachers   = User.objects.filter(email__in=my_invites, role='teacher')
    return render(request, 'management/teachers_list.html', {'teachers': teachers})
