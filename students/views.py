from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count, Sum
from datetime import datetime
from accounts.decorators import role_required
from classrooms.models import Classroom, CourseContent
from assignments.models import Assignment, Submission
from announcements.models import Announcement
from chat.models import Message


def _get_classroom(request, class_id):
    return get_object_or_404(Classroom, pk=class_id, students=request.user)


def _student_layout_context(user, classroom=None, active_nav=None):
    classrooms = user.joined_classrooms.select_related('teacher', 'school').all()
    nav_classroom = classroom or classrooms.first()
    since = user.last_login or timezone.make_aware(datetime.min)
    has_updates = False

    if nav_classroom:
        has_updates = (
            nav_classroom.announcements.filter(created_at__gt=since).exists()
            or nav_classroom.assignments.filter(created_at__gt=since).exists()
            or nav_classroom.course_contents.filter(created_at__gt=since).exists()
        )

    return {
        'classrooms': classrooms,
        'nav_classroom': nav_classroom,
        'unread_count': Message.objects.filter(receiver=user, is_read=False).count(),
        'has_updates': has_updates,
        'active_nav': active_nav,
    }


@role_required('student')
def dashboard(request):
    classrooms    = request.user.joined_classrooms.select_related('teacher', 'school').all()
    classroom     = classrooms.first()
    pending       = []
    total_courses = 0

    for c in classrooms:
        total_courses += c.course_contents.count()
        for a in c.assignments.filter(due_date__gte=timezone.now()):
            if not Submission.objects.filter(assignment=a, student=request.user).exists():
                pending.append(a)

    recent_announcements = Announcement.objects.filter(
        classroom__in=classrooms
    ).order_by('-created_at')[:6]

    context = {
        'classrooms':            classrooms,
        'classroom':             classroom,
        'nav_classroom':         classroom,
        'pending_assignments':   pending,
        'recent_announcements':  recent_announcements,
        'total_courses':         total_courses,
        'unread_count':          Message.objects.filter(receiver=request.user, is_read=False).count(),
        'active_tab':            'dashboard',
        'active_nav':            'dashboard',
    }
    return render(request, 'student/dashboard.html', context)


@role_required('student')
def join_class(request):
    error = None
    if request.method == 'POST':
        code = request.POST.get('class_code', '').strip().upper()
        try:
            classroom = Classroom.objects.get(code=code)
            current_classroom = request.user.joined_classrooms.first()

            if current_classroom and current_classroom != classroom:
                error = f'You are already enrolled in {current_classroom.name}. Leave that class before joining another one.'
            elif current_classroom == classroom:
                error = f'You are already enrolled in {classroom.name}.'
            else:
                classroom.students.add(request.user)
                request.user.role   = 'student'
                request.user.school = classroom.school
                request.user.save()
                messages.success(request, f'Joined {classroom.name}!')
                return redirect('student_dashboard')
        except Classroom.DoesNotExist:
            error = 'Class code not found or invalid. Please try again.'
    context = {'error': error, **_student_layout_context(request.user, active_nav='join_class')}
    return render(request, 'student/join_class.html', context)


@role_required('student')
def leave_classroom(request, class_id):
    classroom = _get_classroom(request, class_id)
    classroom.students.remove(request.user)
    messages.success(request, f'You left {classroom.name}.')
    return redirect('student_dashboard')


@role_required('student')
def classroom_announce(request, class_id):
    classroom     = _get_classroom(request, class_id)
    announcements = Announcement.objects.filter(classroom=classroom)
    context = {
        'classroom': classroom, 'announcements': announcements, 'active_tab': 'announcements',
        **_student_layout_context(request.user, classroom=classroom, active_nav='announcements'),
    }
    return render(request, 'student/classroom_announce.html', context)


@role_required('student')
def classroom_courses(request, class_id):
    classroom = _get_classroom(request, class_id)
    contents  = classroom.course_contents.all()
    units = {}
    for c in contents:
        units.setdefault(c.unit or 'General', []).append(c)
    context = {
        'classroom': classroom, 'units': units, 'active_tab': 'courses',
        **_student_layout_context(request.user, classroom=classroom, active_nav='courses'),
    }
    return render(request, 'student/classroom_courses.html', context)


@role_required('student')
def classroom_classwork(request, class_id):
    classroom = _get_classroom(request, class_id)

    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        assignment    = get_object_or_404(Assignment, pk=assignment_id, classroom=classroom)
        file          = request.FILES.get('file')
        if file:
            sub, created = Submission.objects.get_or_create(
                assignment=assignment, student=request.user, defaults={'file': file}
            )
            if not created:
                if not assignment.is_overdue:
                    sub.file = file
                    sub.save()
                    messages.success(request, 'Submission updated.')
                else:
                    messages.error(request, 'Deadline has passed.')
            else:
                messages.success(request, 'Assignment submitted!')
        return redirect('student_classroom_classwork', class_id=class_id)

    assignment_data = []
    for a in classroom.assignments.all():
        try:    sub = Submission.objects.get(assignment=a, student=request.user)
        except: sub = None
        assignment_data.append({'assignment': a, 'submission': sub})

    context = {
        'classroom': classroom, 'assignment_data': assignment_data, 'active_tab': 'classwork',
        **_student_layout_context(request.user, classroom=classroom, active_nav='classwork'),
    }
    return render(request, 'student/classroom_classwork.html', context)


@role_required('student')
def classroom_peoples(request, class_id):
    classroom = _get_classroom(request, class_id)
    context = {
        'classroom': classroom, 'students': classroom.students.all(), 'active_tab': 'peoples',
        'student_data': [], # Placeholder, actual data would be fetched here if needed
        **_student_layout_context(request.user, classroom=classroom, active_nav='peoples'),
    }
    return render(request, 'student/classroom_peoples.html', context)


@role_required('student')
def classroom_grade(request, class_id):
    classroom   = _get_classroom(request, class_id)
    grade_data  = []
    total_score = total_max = 0

    for a in classroom.assignments.all():
        try:    sub = Submission.objects.get(assignment=a, student=request.user)
        except: sub = None
        grade_data.append({'assignment': a, 'submission': sub})
        if sub and sub.score is not None:
            total_score += sub.score
            total_max   += a.max_score

    overall_pct  = round(total_score / total_max * 100, 1) if total_max else None
    chart_labels = [d['assignment'].title      for d in grade_data if d['submission'] and d['submission'].score is not None]
    chart_scores = [d['submission'].score      for d in grade_data if d['submission'] and d['submission'].score is not None]
    chart_max    = [d['assignment'].max_score  for d in grade_data if d['submission'] and d['submission'].score is not None]

    context = {
        'classroom':   classroom,
        'grade_data':  grade_data,
        'total_score': total_score,
        'total_max':   total_max,
        'overall_pct': overall_pct,
        'chart_labels': chart_labels,
        'chart_scores': chart_scores,
        'chart_max':    chart_max,
        'active_tab':  'grades',
        **_student_layout_context(request.user, classroom=classroom, active_nav='grades'),
    }
    return render(request, 'student/classroom_grade.html', context)


@role_required('student')
def classroom_chat(request, class_id):
    classroom = _get_classroom(request, class_id)
    teacher   = classroom.teacher
    msgs = Message.objects.filter(
        classroom=classroom,
        sender__in=[request.user, teacher],
        receiver__in=[request.user, teacher],
    ).order_by('created_at')
    msgs.filter(receiver=request.user, is_read=False).update(is_read=True)
    context = {
        'classroom':    classroom,
        'teacher':      teacher,
        'chat_messages': msgs,
        'active_tab':   'chat',
        **_student_layout_context(request.user, classroom=classroom, active_nav='chat'),
    }
    return render(request, 'student/classroom_chat.html', context)


@role_required('student')
def unread_count_api(request):
    """JSON endpoint — returns unread message count for the logged-in student."""
    count = Message.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({'unread': count})
