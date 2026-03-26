from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import role_required
from classrooms.models import Classroom, CourseContent
from assignments.models import Assignment, Submission
from announcements.models import Announcement


def _get_classroom(request, class_id):
    return get_object_or_404(Classroom, pk=class_id, students=request.user)


@role_required('student')
def dashboard(request):
    classrooms = request.user.joined_classrooms.select_related('teacher', 'school').all()
    classroom  = classrooms.first()  # student is typically in one class

    pending = []
    total_courses = 0
    for c in classrooms:
        total_courses += c.course_contents.count()
        for a in c.assignments.filter(due_date__gte=timezone.now()):
            if not Submission.objects.filter(assignment=a, student=request.user).exists():
                pending.append(a)

    recent_announcements = Announcement.objects.filter(
        classroom__in=classrooms
    ).order_by('-created_at')[:6]

    return render(request, 'student/dashboard.html', {
        'classrooms': classrooms,
        'classroom': classroom,
        'pending_assignments': pending,
        'recent_announcements': recent_announcements,
        'total_courses': total_courses,
    })


@role_required('student')
def join_class(request):
    error = None
    if request.method == 'POST':
        code = request.POST.get('class_code', '').strip().upper()
        try:
            classroom = Classroom.objects.get(code=code)
            classroom.students.add(request.user)
            request.user.role   = 'student'
            request.user.school = classroom.school
            request.user.save()
            messages.success(request, f'Joined {classroom.name}!')
            return redirect('student_dashboard')
        except Classroom.DoesNotExist:
            error = 'Class code not found. Try again.'
    return render(request, 'student/join_class.html', {'error': error})


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
    return render(request, 'student/classroom_announce.html', {
        'classroom': classroom, 'announcements': announcements, 'active_tab': 'announcements',
    })


@role_required('student')
def classroom_courses(request, class_id):
    classroom = _get_classroom(request, class_id)
    contents  = classroom.course_contents.all()
    units = {}
    for c in contents:
        units.setdefault(c.unit or 'General', []).append(c)
    return render(request, 'student/classroom_courses.html', {
        'classroom': classroom, 'units': units, 'active_tab': 'courses',
    })


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
                    sub.file = file; sub.save()
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

    return render(request, 'student/classroom_classwork.html', {
        'classroom': classroom, 'assignment_data': assignment_data, 'active_tab': 'classwork',
    })


@role_required('student')
def classroom_peoples(request, class_id):
    classroom = _get_classroom(request, class_id)
    return render(request, 'student/classroom_peoples.html', {
        'classroom': classroom, 'students': classroom.students.all(), 'active_tab': 'peoples',
    })


@role_required('student')
def classroom_grade(request, class_id):
    classroom    = _get_classroom(request, class_id)
    assignments  = classroom.assignments.all()
    grade_data   = []
    total_score  = total_max = 0

    for a in assignments:
        try:    sub = Submission.objects.get(assignment=a, student=request.user)
        except: sub = None
        grade_data.append({'assignment': a, 'submission': sub})
        if sub and sub.score is not None:
            total_score += sub.score
            total_max   += a.max_score

    overall_pct   = round(total_score / total_max * 100, 1) if total_max else None
    chart_labels  = [d['assignment'].title   for d in grade_data if d['submission'] and d['submission'].score is not None]
    chart_scores  = [d['submission'].score   for d in grade_data if d['submission'] and d['submission'].score is not None]
    chart_max     = [d['assignment'].max_score for d in grade_data if d['submission'] and d['submission'].score is not None]

    return render(request, 'student/classroom_grade.html', {
        'classroom': classroom, 'grade_data': grade_data,
        'total_score': total_score, 'total_max': total_max,
        'overall_pct': overall_pct,
        'chart_labels': chart_labels,
        'chart_scores': chart_scores,
        'chart_max':    chart_max,
        'active_tab': 'grades',
    })


@role_required('student')
def classroom_chat(request, class_id):
    classroom = _get_classroom(request, class_id)
    teacher   = classroom.teacher
    from chat.models import Message
    msgs = Message.objects.filter(
        classroom=classroom,
        sender__in=[request.user, teacher],
        receiver__in=[request.user, teacher],
    ).order_by('created_at')
    msgs.filter(receiver=request.user, is_read=False).update(is_read=True)
    return render(request, 'student/classroom_chat.html', {
        'classroom': classroom, 'teacher': teacher,
        'messages': msgs, 'active_tab': 'chat',
    })
