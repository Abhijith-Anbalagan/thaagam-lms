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
    # Use timezone-aware now for comparisons with DateTimeField,
    # and localdate() for display / date-only logic
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
        # Attach a plain date so the template can compare safely
        a.due_date_only = a.due_date.date() if a.due_date else None

    total_students    = sum(c.students.count() for c in classrooms)
    total_assignments = all_assignments.count()
    total_submissions = Submission.objects.filter(
        assignment__classroom__in=classrooms
    ).count()
    # Compare DateTimeField with timezone-aware datetime
    due_today = all_assignments.filter(
        due_date__date=today
    ).count()
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
        'today':              today,   # plain date — safe for {{ today|date:"..." }}
    })


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
    announcements = Announcement.objects.filter(
        posted_by=request.user
    ).select_related('classroom').order_by('-created_at')
    return render(request, 'teacher/announcements.html', {'announcements': announcements})


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
                Announcement.objects.create(
                    posted_by=request.user,
                    school=request.user.school,
                    classroom=classroom,
                    title=title,
                    body=body,
                    meet_link=meet_link,
                    is_pinned=is_pinned,
                    target='students',
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
    try:
        from announcements.models import Announcement
        announcements = Announcement.objects.filter(
            school=request.user.school, classroom=classroom
        ).order_by('-is_pinned', '-created_at')
    except Exception:
        announcements = []

    return render(request, 'teacher/classroom_announce.html', {
        'classroom':     classroom,
        'announcements': announcements,
        'active_tab':    'announce',
    })


# ── Courses ───────────────────────────────────────────────────────────────────

@role_required('teacher')
def classroom_courses(request, classroom_id):
    classroom   = _get_classroom(request, classroom_id)
    all_content = CourseContent.objects.filter(classroom=classroom)
    units = {}
    for item in all_content:
        key = item.unit.strip() or 'General'
        units.setdefault(key, []).append(item)

    return render(request, 'teacher/classroom_courses.html', {
        'classroom':  classroom,
        'units':      units,
        'active_tab': 'courses',
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
            sub.score    = score
            sub.feedback = feedback
            sub.save()
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
            # Compare dates safely
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
    from superadmin.models import GlobalCourse
    courses = GlobalCourse.objects.filter(
        school=request.user.school, status='published'
    )
    return render(request, 'teacher/my_learning.html', {'courses': courses})


# ── Chat ──────────────────────────────────────────────────────────────────────

@role_required('teacher')
def classroom_chat(request, classroom_id):
    classroom = _get_classroom(request, classroom_id)
    try:
        from chat.models import Message
        chat_messages = Message.objects.filter(
            classroom=classroom
        ).select_related('sender').order_by('created_at')
    except Exception:
        chat_messages = []

    return render(request, 'teacher/classroom_chat.html', {
        'classroom':     classroom,
        'chat_messages': chat_messages,
        'active_tab':    'chat',
    })
