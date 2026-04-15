import string
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Max
from django.contrib import messages
from accounts.decorators import role_required
from classrooms.models import Classroom, CourseContent
from classrooms.forms import ClassroomForm
from assignments.models import Assignment, Submission
from chat.realtime import notify_user, notify_users


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_classroom(request, classroom_id):
    return get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user,
        school=request.user.school
    )


def _grade_letter(pct):
    if pct is None: return '—'
    if pct >= 90: return 'A'
    if pct >= 75: return 'B'
    if pct >= 60: return 'C'
    if pct >= 40: return 'D'
    return 'F'


# ── Dashboard ─────────────────────────────────────────────────────────────────

@role_required('teacher')
def teacher_dashboard(request):
    now   = timezone.now()
    today = timezone.localdate()

    classrooms = Classroom.objects.filter(
        teacher=request.user,
        school=request.user.school
    ).prefetch_related('students', 'assignments')

    for classroom in classrooms:
        classroom.ungraded_count = Submission.objects.filter(
            assignment__classroom=classroom, score__isnull=True
        ).count()

    all_assignments = Assignment.objects.filter(
        classroom__in=classrooms
    ).select_related('classroom')

    recent_assignments = list(all_assignments.order_by('-due_date')[:5])
    for a in recent_assignments:
        a.submission_count = Submission.objects.filter(assignment=a).count()
        a.is_graded = (
            a.submission_count > 0
            and not Submission.objects.filter(assignment=a, score__isnull=True).exists()
        )
        a.due_date_only = a.due_date.date() if a.due_date else None

    total_students    = sum(c.students.count() for c in classrooms)
    total_assignments = all_assignments.count()
    total_submissions = Submission.objects.filter(
        assignment__classroom__in=classrooms
    ).count()
    due_today = all_assignments.filter(due_date__date=today).count()
    pending_grading = Submission.objects.filter(
        assignment__classroom__in=classrooms, score__isnull=True
    ).count()

    graded       = Submission.objects.filter(
        assignment__classroom__in=classrooms, score__isnull=False
    )
    total_graded = graded.count()

    def _pct(lo, hi, max_s=20):
        if not total_graded: return 0
        n = graded.filter(
            score__gte=lo / 100 * max_s,
            score__lte=hi / 100 * max_s
        ).count()
        return round(n / total_graded * 100)

    avg_score = top_score = 0
    if total_graded:
        agg       = graded.aggregate(avg=Avg('score'), top=Max('score'))
        avg_score = round((agg['avg'] / 20) * 100) if agg['avg'] else 0
        top_score = round(agg['top']) if agg['top'] else 0

    recent_submissions = Submission.objects.filter(
        assignment__classroom__in=classrooms
    ).select_related(
        'student', 'assignment', 'assignment__classroom'
    ).order_by('-submitted_at')[:5]

    try:
        from announcements.models import Announcement
        announcements = Announcement.objects.filter(
            school=request.user.school
        ).order_by('-is_pinned', '-created_at')[:5]
    except Exception:
        announcements = []

    return render(request, 'teacher/dashboard.html', {
        'classrooms':         classrooms,
        'recent_assignments': recent_assignments,
        'recent_submissions': recent_submissions,
        'announcements':      announcements,
        'total_students':     total_students,
        'total_assignments':  total_assignments,
        'total_submissions':  total_submissions,
        'due_today':          due_today,
        'pending_grading':    pending_grading,
        'avg_score':          avg_score,
        'top_score':          top_score,
        'grade_a_pct':        _pct(90, 100),
        'grade_b_pct':        _pct(75, 89),
        'grade_c_pct':        _pct(60, 74),
        'grade_d_pct':        _pct(40, 59),
        'today':              today,
    })


# ── Classroom Detail ──────────────────────────────────────────────────────────
@role_required('teacher')
def classroom_detail(request, classroom_id):
    """
    Unified classroom page — all tabs render inline on the same URL.
    Handles POST for announce, classwork grading, people removal, and grade saving.
    """
    from django.utils import timezone as tz

    classroom = _get_classroom(request, classroom_id)

    # ── Handle POSTs from inline forms ───────────────────────────────────────
    if request.method == 'POST':
        action = request.POST.get('_action', '')

        # Announce post
        if action == 'announce' or request.POST.get('title') and request.POST.get('body') and not request.POST.get('submission_id') and not request.POST.get('remove_student'):
            from announcements.models import Announcement
            title     = request.POST.get('title', '').strip()
            body      = request.POST.get('body', '').strip()
            meet_link = request.POST.get('meet_link', '').strip()
            is_pinned = bool(request.POST.get('is_pinned'))
            if title and body:
                Announcement.objects.create(
                    posted_by=request.user, school=request.user.school,
                    classroom=classroom, title=title, body=body,
                    meet_link=meet_link, is_pinned=is_pinned, target='students',
                )
                messages.success(request, 'Announcement posted.')

        # Grade save
        elif request.POST.get('submission_id') and request.POST.get('score'):
            sub_id   = request.POST.get('submission_id')
            score    = request.POST.get('score')
            feedback = request.POST.get('feedback', '')
            sub = get_object_or_404(Submission, id=sub_id, assignment__classroom=classroom)
            sub.score = score; sub.feedback = feedback; sub.save()
            messages.success(request, 'Grade saved.')

        # Remove student
        elif request.POST.get('remove_student'):
            student_id = request.POST.get('remove_student')
            classroom.students.remove(student_id)
            notify_students([student_id], {'type': 'forced_redirect', 'url': '/student/join/'})
            messages.success(request, 'Student removed.')

        # Delete Announcement
        elif action == 'delete_announcement':
            from announcements.models import Announcement
            ann_id = request.POST.get('announcement_id')
            ann = get_object_or_404(Announcement, id=ann_id, classroom=classroom)
            ann.delete()
            messages.success(request, 'Announcement deleted.')

        # Create assignment
        elif request.POST.get('title') and not request.POST.get('body'):
            from assignments.forms import AssignmentForm
            form = AssignmentForm(request.POST, request.FILES)
            if form.is_valid():
                a = form.save(commit=False); a.classroom = classroom; a.save()
                messages.success(request, f'Assignment "{a.title}" created.')

        tab = request.POST.get('_tab', '')
        redirect_url = f"{request.path}?tab={tab}" if tab else request.path
        return redirect(redirect_url)

    today    = tz.localdate()
    students = classroom.students.all()

    # ── Student stats (shared by Home + People tabs) ───────────────────────
    total_assignments = Assignment.objects.filter(classroom=classroom).count()
    student_data = []
    for student in students:
        submitted    = Submission.objects.filter(assignment__classroom=classroom, student=student).count()
        graded_subs  = Submission.objects.filter(assignment__classroom=classroom, student=student, score__isnull=False)
        graded_count = graded_subs.count()
        total_score  = sum(s.score for s in graded_subs)
        avg = round((total_score / (graded_count * 20)) * 100) if graded_count else 0
        student_data.append({
            'user': student, 'submitted': submitted,
            'total_assignments': total_assignments,
            'avg_pct': avg, 'grade_letter': _grade_letter(avg),
        })

    # ── Avg score for hero ─────────────────────────────────────────────────
    graded    = Submission.objects.filter(assignment__classroom=classroom, score__isnull=False)
    avg_score = 0
    if graded.exists():
        from django.db.models import Avg
        agg = graded.aggregate(avg=Avg('score'))
        avg_score = round((agg['avg'] / 20) * 100) if agg['avg'] else 0

    # ── Announcements ──────────────────────────────────────────────────────
    try:
        from announcements.models import Announcement
        announcements = Announcement.objects.filter(
            school=request.user.school, classroom=classroom
        ).order_by('-is_pinned', '-created_at')
    except Exception:
        announcements = []

    # ── Assignments (classwork tab) ────────────────────────────────────────
    assignments = Assignment.objects.filter(classroom=classroom).order_by('-due_date')
    for a in assignments:
        a.submission_count = Submission.objects.filter(assignment=a).count()
        a.ungraded_count   = Submission.objects.filter(assignment=a, score__isnull=True).count()
        a.total_students   = classroom.students.count()
        a.due_date_only    = a.due_date.date() if a.due_date else None

    # ── Progress data ──────────────────────────────────────────────────────
    ordered_assignments = Assignment.objects.filter(classroom=classroom).order_by('due_date')
    student_progress = []
    for student in students:
        rows = []
        total_earned = total_possible = 0
        for assignment in ordered_assignments:
            sub       = Submission.objects.filter(assignment=assignment, student=student).first()
            score_val = sub.score if sub and sub.score is not None else None
            max_score = assignment.max_score
            pct       = round((score_val / max_score) * 100) if score_val is not None else None
            late      = bool(sub and assignment.due_date and sub.submitted_at.date() > assignment.due_date.date())
            if score_val is not None:
                total_earned += score_val; total_possible += max_score
            rows.append({
                'assignment': assignment, 'submission': sub,
                'score': score_val, 'max_score': max_score,
                'pct': pct, 'grade_letter': _grade_letter(pct), 'is_late': late,
            })
        overall_pct = round((total_earned / total_possible) * 100) if total_possible else 0
        student_progress.append({
            'student': student, 'rows': rows,
            'overall_pct': overall_pct, 'overall_grade': _grade_letter(overall_pct),
            'total_earned': total_earned, 'total_possible': total_possible,
        })

    # ── Courses ────────────────────────────────────────────────────────────
    try:
        from superadmin.models import GlobalCourse, ClassroomCourseAssignment
        all_courses = GlobalCourse.objects.filter(
            schools=request.user.school, status='published'
        ).prefetch_related('concepts')
        assigned_course_ids = set(
            ClassroomCourseAssignment.objects.filter(classroom=classroom).values_list('course_id', flat=True)
        )
    except Exception:
        all_courses = []; assigned_course_ids = set()

    # ── Chat ───────────────────────────────────────────────────────────────
    selected_student = None
    chat_messages    = []
    selected_student_online = False
    student_pk = request.GET.get('student')
    if student_pk:
        try:
            selected_student = classroom.students.get(pk=student_pk)
            from chat.models import Message
            chat_messages = Message.objects.filter(
                classroom=classroom
            ).select_related('sender').order_by('created_at')
        except Exception:
            pass

    if selected_student:
        from django.core.cache import cache
        from django.contrib.sessions.models import Session
        cached = cache.get(f'user_online_{selected_student.pk}')
        if cached is None:
            active_ids = set()
            for s in Session.objects.filter(expire_date__gt=timezone.now()):
                try:
                    uid = s.get_decoded().get('_auth_user_id')
                    if uid: active_ids.add(int(uid))
                except Exception:
                    pass
            selected_student_online = selected_student.pk in active_ids
            if selected_student_online:
                cache.set(f'user_online_{selected_student.pk}', True, timeout=None)
        else:
            selected_student_online = cached is True

    assigned_course_count = len(assigned_course_ids)
    assignment_count      = Assignment.objects.filter(classroom=classroom).count()

    # Check teacher completion for each course
    from superadmin.models import GlobalConcept, ConceptProgress
    teacher_completed_ids = set()
    for course in all_courses:
        total_concepts = course.concepts.count()
        if total_concepts > 0:
            completed_concepts = ConceptProgress.objects.filter(
                student=request.user, 
                concept__course=course
            ).count()
            if completed_concepts >= total_concepts:
                teacher_completed_ids.add(course.pk)

    return render(request, 'teacher/classroom_detail.html', {
        'classroom':             classroom,
        'student_data':          student_data,
        'avg_score':             avg_score,
        'announcements':         announcements,
        'assignments':           assignments,
        'student_progress':      student_progress,
        'all_courses':           all_courses,
        'assigned_course_ids':   assigned_course_ids,
        'assigned_course_count': assigned_course_count,
        'teacher_completed_ids': teacher_completed_ids,
        'assignment_count':      assignment_count,
        'chat_students':         students,
        'selected_student':      selected_student,
        'selected_student_online': selected_student_online,
        'chat_messages':         chat_messages,
        'today':                 today,
    })

# ── Assign / Unassign Course to Classroom (AJAX) ─────────────────────────────

@role_required('teacher')
def assign_course_to_classroom(request, classroom_id, course_id):
    """
    POST  → toggle a GlobalCourse assignment on a classroom.
    Returns JSON: { assigned: true/false }
    """
    from django.http import JsonResponse
    from superadmin.models import GlobalCourse, ClassroomCourseAssignment

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    classroom = _get_classroom(request, classroom_id)
    course    = get_object_or_404(
        GlobalCourse,
        pk=course_id,
        schools=request.user.school,
        status='published'
    )

    obj, created = ClassroomCourseAssignment.objects.get_or_create(
        classroom=classroom,
        course=course,
    )
    if not created:
        obj.delete()
        return JsonResponse({'assigned': False})

    return JsonResponse({'assigned': True})


# ── Create Classroom ──────────────────────────────────────────────────────────

@role_required('teacher')
def create_classroom(request):
    form = ClassroomForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        classroom         = form.save(commit=False)
        classroom.teacher = request.user
        classroom.school  = request.user.school
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not Classroom.objects.filter(code=code).exists():
                break
        classroom.code = code
        classroom.save()
        messages.success(request, f'Classroom "{classroom.name}" created! Code: {code}')
        return redirect('teacher_dashboard')

    return render(request, 'teacher/classroom.html', {
        'form':       form,
        'active_tab': 'create',
    })


# ── All Announcements ────────────────────────────────────────────────────────

@role_required('teacher')
def teacher_announcements(request):
    from announcements.models import Announcement
    from django.utils import timezone
    from datetime import timedelta

    # 1. Automatical delete: clean up announcements expired > 1 day ago
    # This runs every time a teacher visits their announcements page.
    Announcement.objects.filter(
        expires_at__lt=timezone.now() - timedelta(days=1)
    ).delete()

    classrooms = Classroom.objects.filter(
        teacher=request.user, school=request.user.school
    )

    # 2. Handle Posting (Unified View)
    if request.method == 'POST':
        title      = request.POST.get('title', '').strip()
        body       = request.POST.get('body', '').strip()
        meet_link  = request.POST.get('meet_link', '').strip()
        is_pinned  = bool(request.POST.get('is_pinned'))
        expiry_days = request.POST.get('expiry_days')  # New: Number of days until expiry
        classroom_ids = request.POST.getlist('classrooms')

        if title and body and classroom_ids:
            # Default to 7 days if no expiry is chosen to keep the system clean
            expires_at = timezone.now() + timedelta(days=7)
            if expiry_days and expiry_days.isdigit():
                expires_at = timezone.now() + timedelta(days=int(expiry_days))

            for cid in classroom_ids:
                classroom = get_object_or_404(Classroom, pk=cid, teacher=request.user)
                announcement = Announcement.objects.create(
                    posted_by=request.user,
                    school=request.user.school,
                    classroom=classroom,
                    title=title,
                    body=body,
                    meet_link=meet_link,
                    is_pinned=is_pinned,
                    expires_at=expires_at,
                    target='students',
                )
                notify_users(
                    classroom.students.values_list('id', flat=True),
                    {
                        'type': 'announcement',
                        'classroom_id': classroom.id,
                        'redirect_url': f'/student/classroom/{classroom.id}/announce/',
                        'title': announcement.title,
                    },
                )
            messages.success(request, 'Announcement posted successfully.')
            return redirect('teacher_announcements')
        else:
            messages.error(request, 'Please fill in all required fields and select at least one classroom.')

    # 3. List History
    announcements = Announcement.objects.filter(
        posted_by=request.user
    ).select_related('classroom').order_by('-created_at')

    return render(request, 'teacher/announcements.html', {
        'announcements': announcements,
        'classrooms': classrooms
    })


# ── Post Announcement (dashboard button) ─────────────────────────────────────

@role_required('teacher')
def post_announcement(request):
    from announcements.models import Announcement
    classrooms = Classroom.objects.filter(
        teacher=request.user, school=request.user.school
    )
    if request.method == 'POST':
        title      = request.POST.get('title', '').strip()
        body       = request.POST.get('body', '').strip()
        meet_link  = request.POST.get('meet_link', '').strip()
        is_pinned  = bool(request.POST.get('is_pinned'))
        classroom_ids = request.POST.getlist('classrooms')
        if title and body and classroom_ids:
            for cid in classroom_ids:
                classroom = get_object_or_404(Classroom, pk=cid, teacher=request.user)
                announcement = Announcement.objects.create(
                    posted_by=request.user,
                    school=request.user.school,
                    classroom=classroom,
                    title=title,
                    body=body,
                    meet_link=meet_link,
                    is_pinned=is_pinned,
                    target='students',
                )
                notify_users(
                    classroom.students.values_list('id', flat=True),
                    {
                        'type': 'announcement',
                        'classroom_id': classroom.id,
                        'redirect_url': f'/student/classroom/{classroom.id}/announce/',
                        'title': announcement.title,
                    },
                )
            messages.success(request, 'Announcement posted successfully.')
            return redirect('teacher_dashboard')
        else:
            messages.error(request, 'Please fill in all required fields and select at least one classroom.')
    return render(request, 'teacher/post_announcement.html', {'classrooms': classrooms})


# ── Announce ──────────────────────────────────────────────────────────────────

@role_required('teacher')
def classroom_announce(request, classroom_id):
    classroom = _get_classroom(request, classroom_id)
    from announcements.models import Announcement
    from django.utils import timezone
    from datetime import timedelta

    # Cleanup expired
    Announcement.objects.filter(classroom=classroom, expires_at__lt=timezone.now() - timedelta(days=1)).delete()

    if request.method == 'POST':
        title     = request.POST.get('title', '').strip()
        body      = request.POST.get('body', '').strip()
        meet_link = request.POST.get('meet_link', '').strip()
        is_pinned = bool(request.POST.get('is_pinned'))
        expiry_days = request.POST.get('expiry_days')
        if title and body:
            expires_at = None
            if expiry_days and expiry_days.isdigit():
                expires_at = timezone.now() + timedelta(days=int(expiry_days))

            announcement = Announcement.objects.create(
                posted_by=request.user,
                school=request.user.school,
                classroom=classroom,
                title=title,
                body=body,
                meet_link=meet_link,
                is_pinned=is_pinned,
                expires_at=expires_at,
                target='students',
            )
            notify_users(
                classroom.students.values_list('id', flat=True),
                {
                    'type': 'announcement',
                    'classroom_id': classroom.id,
                    'redirect_url': f'/student/classroom/{classroom.id}/announce/',
                    'title': announcement.title,
                },
            )
            messages.success(request, 'Announcement posted.')
        else:
            messages.error(request, 'Title and message are required.')
        return redirect('teacher_classroom_announce', classroom_id=classroom_id)

    announcements = Announcement.objects.filter(
        school=request.user.school, classroom=classroom
    ).order_by('-is_pinned', '-created_at')

    return render(request, 'teacher/classroom_announce.html', {
        'classroom':     classroom,
        'announcements': announcements,
        'active_tab':    'announce',
    })


# ── Courses ───────────────────────────────────────────────────────────────────
# Replace the existing classroom_courses view in classrooms/views/teacher_views.py

@role_required('teacher')
def classroom_courses(request, classroom_id):
    classroom = _get_classroom(request, classroom_id)

    try:
        from superadmin.models import GlobalCourse, ClassroomCourseAssignment

        # All published courses for the school
        all_courses = GlobalCourse.objects.filter(
            schools=request.user.school,
            status='published'
        ).prefetch_related('concepts')

        # IDs already assigned to THIS classroom
        assigned_course_ids = set(
            ClassroomCourseAssignment.objects.filter(
                classroom=classroom
            ).values_list('course_id', flat=True)
        )

        # Courses actually assigned to this classroom
        assigned_courses = [c for c in all_courses if c.pk in assigned_course_ids]

    except Exception:
        all_courses         = []
        assigned_course_ids = set()
        assigned_courses    = []

    return render(request, 'teacher/classroom_courses.html', {
        'classroom':            classroom,
        'all_courses':          all_courses,
        'assigned_courses':     assigned_courses,
        'assigned_course_ids':  assigned_course_ids,
        'active_tab':           'courses',
    })

# ── Classwork ─────────────────────────────────────────────────────────────────

@role_required('teacher')
def classroom_classwork(request, classroom_id):
    classroom   = _get_classroom(request, classroom_id)
    assignments = Assignment.objects.filter(
        classroom=classroom
    ).order_by('-due_date')

    for a in assignments:
        a.submission_count = Submission.objects.filter(assignment=a).count()
        a.ungraded_count   = Submission.objects.filter(assignment=a, score__isnull=True).count()
        a.total_students   = classroom.students.count()

    from assignments.forms import AssignmentForm
    form = AssignmentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        assignment           = form.save(commit=False)
        assignment.classroom = classroom
        assignment.save()
        notify_users(
            classroom.students.values_list('id', flat=True),
            {
                'type': 'assignment',
                'classroom_id': classroom.id,
                'redirect_url': f'/student/classroom/{classroom.id}/classwork/',
                'title': assignment.title,
            },
        )
        messages.success(request, f'Assignment "{assignment.title}" created.')
        return redirect('teacher_classroom_classwork', classroom_id=classroom_id)

    return render(request, 'teacher/classroom_classwork.html', {
        'classroom':   classroom,
        'assignments': assignments,
        'form':        form,
        'active_tab':  'classwork',
        'today':       timezone.localdate(),
    })


# ── Peoples ───────────────────────────────────────────────────────────────────

@role_required('teacher')
def classroom_peoples(request, classroom_id):
    classroom = _get_classroom(request, classroom_id)

    if request.method == 'POST':
        student_id = request.POST.get('remove_student')
        if student_id:
            classroom.students.remove(student_id)
            notify_students([student_id], {'type': 'forced_redirect', 'url': '/student/join/'})
            messages.success(request, 'Student removed.')
            return redirect('teacher_classroom_peoples', classroom_id=classroom_id)

    students          = classroom.students.all()
    total_assignments = Assignment.objects.filter(classroom=classroom).count()

    student_data = []
    for student in students:
        submitted    = Submission.objects.filter(
            assignment__classroom=classroom, student=student
        ).count()
        graded_subs  = Submission.objects.filter(
            assignment__classroom=classroom, student=student, score__isnull=False
        )
        graded_count = graded_subs.count()
        total_score  = sum(s.score for s in graded_subs)
        avg = round((total_score / (graded_count * 20)) * 100) if graded_count else 0

        student_data.append({
            'user':              student,
            'submitted':         submitted,
            'total_assignments': total_assignments,
            'avg_pct':           avg,
            'grade_letter':      _grade_letter(avg),
        })

    return render(request, 'teacher/classroom_peoples.html', {
        'classroom':    classroom,
        'student_data': student_data,
        'active_tab':   'peoples',
    })


# ── Grades ────────────────────────────────────────────────────────────────────

@role_required('teacher')
def classroom_grade(request, classroom_id):
    classroom   = _get_classroom(request, classroom_id)
    students    = classroom.students.all()
    assignments = Assignment.objects.filter(
        classroom=classroom
    ).order_by('due_date')

    if request.method == 'POST':
        sub_id   = request.POST.get('submission_id')
        score    = request.POST.get('score')
        feedback = request.POST.get('feedback', '')
        if sub_id and score:
            sub          = get_object_or_404(
                Submission, id=sub_id, assignment__classroom=classroom
            )
            was_ungraded = sub.score is None
            sub.score    = score
            sub.feedback = feedback
            sub.save()
            if was_ungraded and sub.score is not None:
                notify_user(
                    sub.student_id,
                    {
                        'type': 'grade',
                        'classroom_id': classroom.id,
                        'redirect_url': f'/student/classroom/{classroom.id}/grades/',
                        'title': sub.assignment.title,
                    },
                )
            messages.success(request, 'Grade saved.')
            return redirect('teacher_classroom_grade', classroom_id=classroom_id)

    today = timezone.localdate()

    student_progress = []
    for student in students:
        rows = []
        total_earned = total_possible = 0
        for assignment in assignments:
            sub       = Submission.objects.filter(
                assignment=assignment, student=student
            ).first()
            score_val = sub.score if sub and sub.score is not None else None
            max_score = assignment.max_score
            pct       = round((score_val / max_score) * 100) if score_val is not None else None
            late = bool(
                sub and assignment.due_date
                and sub.submitted_at.date() > assignment.due_date.date()
            )

            if score_val is not None:
                total_earned   += score_val
                total_possible += max_score

            rows.append({
                'assignment':   assignment,
                'submission':   sub,
                'score':        score_val,
                'max_score':    max_score,
                'pct':          pct,
                'grade_letter': _grade_letter(pct),
                'is_late':      late,
            })

        overall_pct = round(
            (total_earned / total_possible) * 100
        ) if total_possible else 0
        student_progress.append({
            'student':        student,
            'rows':           rows,
            'overall_pct':    overall_pct,
            'overall_grade':  _grade_letter(overall_pct),
            'total_earned':   total_earned,
            'total_possible': total_possible,
        })

    return render(request, 'teacher/classroom_grade.html', {
        'classroom':        classroom,
        'assignments':      assignments,
        'student_progress': student_progress,
        'active_tab':       'grades',
    })


# ── My Classrooms ───────────────────────────────────────────────────────────

@role_required('teacher')
def my_classrooms(request):
    classrooms = Classroom.objects.filter(
        teacher=request.user,
        school=request.user.school
    ).prefetch_related('students', 'assignments')
    for classroom in classrooms:
        classroom.ungraded_count = Submission.objects.filter(
            assignment__classroom=classroom, score__isnull=True
        ).count()
    return render(request, 'teacher/my_classrooms.html', {'classrooms': classrooms})


# ── My Learning ───────────────────────────────────────────────────────────────

@role_required('teacher')
def my_learning(request):
    from superadmin.models import GlobalCourse, CourseEnrollment

    available_courses = GlobalCourse.objects.filter(
        schools=request.user.school,
        status='published'
    ).prefetch_related('concepts', 'enrollments')

    enrollments = {
        enrollment.course_id: enrollment
        for enrollment in CourseEnrollment.objects.filter(user=request.user).select_related('course')
    }
    enrolled_ids = set(enrollments.keys())

    enrolled_courses = []
    unenrolled_courses = []
    for course in available_courses:
        course.enrollment = enrollments.get(course.pk)
        if course.pk in enrolled_ids:
            enrolled_courses.append(course)
        else:
            unenrolled_courses.append(course)

    return render(request, 'teacher/my_learning.html', {
        'enrolled_courses':   enrolled_courses,
        'unenrolled_courses': unenrolled_courses,
        'enrolled_ids':       enrolled_ids,
        'enrollments':        enrollments,
    })

@role_required('teacher')
def teacher_course_detail(request, course_id):
    from superadmin.models import CourseEnrollment, ConceptProgress
 
    enrollment = get_object_or_404(
        CourseEnrollment.objects.select_related('course'),
        user=request.user,
        course_id=course_id,
        course__schools=request.user.school,
        course__status='published',
    )
    course   = enrollment.course
    concepts = course.concepts.prefetch_related('videos').all()
 
    beginner_concepts     = concepts.filter(level='beginner')
    intermediate_concepts = concepts.filter(level='intermediate')
    advanced_concepts     = concepts.filter(level='advanced')
 
    # ── Progress ──────────────────────────────────────────────────────────────
    completed_ids   = set(
        ConceptProgress.objects.filter(student=request.user, concept__course=course)
        .values_list('concept_id', flat=True)
    )
    total_concepts  = concepts.count()
    completed_count = len(completed_ids)
    progress_pct    = round((completed_count / total_concepts) * 100) if total_concepts else 0
 
    return render(request, 'teacher/course_detail.html', {
        'course':                 course,
        'concepts':               concepts,
        'beginner_concepts':      beginner_concepts,
        'intermediate_concepts':  intermediate_concepts,
        'advanced_concepts':      advanced_concepts,
        'enrollment':             enrollment,
        'total_concepts':         total_concepts,
        'completed_ids':          completed_ids,
        'completed_count':        completed_count,
        'progress_pct':           progress_pct,
    })
 


@role_required('teacher')
def teacher_course_concept(request, course_id, concept_id):
    import json
    from superadmin.models import CourseEnrollment, GlobalConcept, ConceptProgress

    enrollment = get_object_or_404(
        CourseEnrollment.objects.select_related('course'),
        user=request.user, course_id=course_id,
        course__schools=request.user.school, course__status='published',
    )
    course   = enrollment.course
    concept  = get_object_or_404(GlobalConcept, pk=concept_id, course=course)
    concepts = list(course.concepts.prefetch_related('videos').order_by('order', 'created_at'))

    completed_ids = set(
        ConceptProgress.objects.filter(student=request.user, concept__course=course)
        .values_list('concept_id', flat=True)
    )

    # Enforce sequential access — redirect to first incomplete if trying to skip
    idx = next((i for i, c in enumerate(concepts) if c.pk == concept.pk), 0)
    if idx > 0 and concepts[idx - 1].pk not in completed_ids:
        first_incomplete = next((c for c in concepts if c.pk not in completed_ids), concepts[0])
        return redirect('teacher_course_concept', course_id=course.pk, concept_id=first_incomplete.pk)

    prev_concept = concepts[idx - 1] if idx > 0 else None
    # Next is only accessible after current is completed
    next_concept = concepts[idx + 1] if (idx < len(concepts) - 1 and concept.pk in completed_ids) else None

    total_concepts  = len(concepts)
    completed_count = len(completed_ids)
    progress_pct    = round((completed_count / total_concepts) * 100) if total_concepts else 0

    raw_quiz = concept.quiz
    if isinstance(raw_quiz, str) and raw_quiz.strip():
        try:
            quiz_data = json.loads(raw_quiz)
        except (json.JSONDecodeError, ValueError):
            quiz_data = []
    elif isinstance(raw_quiz, list):
        quiz_data = raw_quiz
    else:
        quiz_data = []

    return render(request, 'teacher/course_concept.html', {
        'course':                course,
        'concept':               concept,
        'quiz_data':             quiz_data,
        'enrollment':            enrollment,
        'prev_concept':          prev_concept,
        'next_concept':          next_concept,
        'total_concepts':        total_concepts,
        'completed_count':       completed_count,
        'completed_ids':         completed_ids,
        'progress_pct':          progress_pct,
        'beginner_concepts':     [c for c in concepts if c.level == 'beginner'],
        'intermediate_concepts': [c for c in concepts if c.level == 'intermediate'],
        'advanced_concepts':     [c for c in concepts if c.level == 'advanced'],
        'all_concepts':          concepts,
    })


@role_required('teacher')
def teacher_mark_concept_complete(request, course_id, concept_id):
    from superadmin.models import CourseEnrollment, GlobalConcept, ConceptProgress
    from django.http import HttpResponseNotAllowed

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    enrollment = get_object_or_404(
        CourseEnrollment,
        user=request.user, course_id=course_id,
        course__schools=request.user.school, course__status='published',
    )
    course   = enrollment.course
    concept  = get_object_or_404(GlobalConcept, pk=concept_id, course=course)
    concepts = list(course.concepts.order_by('order', 'created_at'))

    # Enforce sequential — only allow if previous is done
    idx = next((i for i, c in enumerate(concepts) if c.pk == concept.pk), 0)
    completed_ids = set(
        ConceptProgress.objects.filter(student=request.user, concept__course=course)
        .values_list('concept_id', flat=True)
    )
    if idx > 0 and concepts[idx - 1].pk not in completed_ids:
        return redirect('teacher_course_concept', course_id=course.pk, concept_id=concept.pk)

    ConceptProgress.objects.get_or_create(student=request.user, concept=concept)

    # Redirect to next concept if available
    next_concept = concepts[idx + 1] if idx < len(concepts) - 1 else None
    if next_concept:
        return redirect('teacher_course_concept', course_id=course.pk, concept_id=next_concept.pk)
    return redirect('teacher_course_detail', course_id=course.pk)

@role_required('teacher')
def course_enroll(request, course_id):
    from superadmin.models import GlobalCourse, CourseEnrollment
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    course = get_object_or_404(
        GlobalCourse,
        pk=course_id,
        schools=request.user.school,
        status='published'
    )

    enrollment, created = CourseEnrollment.objects.get_or_create(
        user=request.user, course=course
    )
    if not created:
        enrollment.delete()
        return JsonResponse({'enrolled': False})

    return JsonResponse({
        'enrolled': True,
        'deadline': timezone.localtime(enrollment.deadline_at).strftime('%b %d, %Y'),
        'course_url': f'/teacher/my-learning/{course.pk}/',
    })


# ── Messages ─────────────────────────────────────────────────────────────────

@role_required('teacher')
def teacher_messages(request):
    classrooms = Classroom.objects.filter(
        teacher=request.user,
        school=request.user.school
    ).prefetch_related('students')

    try:
        from chat.models import Message
        classroom_chats = []
        for classroom in classrooms:
            latest_msg = Message.objects.filter(
                classroom=classroom
            ).select_related('sender').order_by('-created_at').first()

            unread_count = Message.objects.filter(
                classroom=classroom,
                is_read=False
            ).exclude(sender=request.user).count()

            classroom_chats.append({
                'classroom':    classroom,
                'latest_msg':   latest_msg,
                'unread_count': unread_count,
            })
        classroom_chats.sort(
            key=lambda x: x['latest_msg'].created_at if x['latest_msg'] else timezone.datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )
    except Exception:
        classroom_chats = [{'classroom': c, 'latest_msg': None, 'unread_count': 0} for c in classrooms]

    return render(request, 'teacher/messages.html', {
        'classroom_chats': classroom_chats,
    })


# ── Chat ──────────────────────────────────────────────────────────────────────

@role_required('teacher')
def classroom_chat(request, classroom_id):
    classroom = _get_classroom(request, classroom_id)
    from chat.models import Message

    from django.db.models import Count, Q
    students = classroom.students.all().annotate(
        unread_count=Count('sent_messages', filter=Q(sent_messages__receiver=request.user, sent_messages__is_read=False, sent_messages__classroom=classroom))
    ).order_by('first_name', 'username', 'email')
    
    student_id = request.GET.get('student')
    selected_student = None
    chat_messages = []

    if student_id:
        selected_student = get_object_or_404(students, pk=student_id)
    elif students.exists():
        selected_student = students.first()

    if selected_student:
        chat_messages = Message.objects.filter(
            classroom=classroom,
            sender__in=[request.user, selected_student],
            receiver__in=[request.user, selected_student],
        ).select_related('sender').order_by('created_at')
        
        # Mark as read
        Message.objects.filter(
            classroom=classroom,
            sender=selected_student,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)

    # Check student online status
    selected_student_online = False
    if selected_student:
        from django.core.cache import cache
        from django.contrib.sessions.models import Session
        cached = cache.get(f'user_online_{selected_student.pk}')
        if cached is None:
            active_ids = set()
            for s in Session.objects.filter(expire_date__gt=timezone.now()):
                try:
                    uid = s.get_decoded().get('_auth_user_id')
                    if uid: active_ids.add(int(uid))
                except Exception:
                    pass
            selected_student_online = selected_student.pk in active_ids
            if selected_student_online:
                cache.set(f'user_online_{selected_student.pk}', True, timeout=None)
        else:
            selected_student_online = cached is True

    return render(request, 'teacher/classroom_chat.html', {
        'classroom':              classroom,
        'students':               students,
        'selected_student':       selected_student,
        'selected_student_online': selected_student_online,
        'chat_messages':          chat_messages,
        'active_tab':             'chat',
    })