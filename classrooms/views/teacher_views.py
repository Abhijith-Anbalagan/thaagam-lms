from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import role_required
from classrooms.models import Classroom, CourseContent
from assignments.models import Assignment, Submission


def _classroom(request, classroom_id):
    return get_object_or_404(Classroom, pk=classroom_id, teacher=request.user)


@role_required('teacher')
def dashboard(request):
    classrooms = Classroom.objects.filter(teacher=request.user)
    pending    = Submission.objects.filter(
        assignment__classroom__teacher=request.user, score__isnull=True
    ).select_related('assignment', 'student')
    return render(request, 'teacher/dashboard.html', {
        'classrooms': classrooms, 'pending_submissions': pending,
    })


@role_required('teacher')
def create_classroom(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            c = Classroom.objects.create(name=name, teacher=request.user, school=request.user.school)
            messages.success(request, f'Classroom created! Code: {c.code}')
            return redirect('teacher_classroom_announce', classroom_id=c.pk)
    return render(request, 'teacher/classroom.html', {'mode': 'create'})


@role_required('teacher')
def classroom_announce(request, classroom_id):
    classroom = _classroom(request, classroom_id)
    from announcements.models import Announcement
    announcements = Announcement.objects.filter(classroom=classroom)
    if request.method == 'POST':
        Announcement.objects.create(
            posted_by=request.user, school=classroom.school, classroom=classroom,
            title=request.POST.get('title', '').strip(),
            body=request.POST.get('body', '').strip(),
            meet_link=request.POST.get('meet_link', '').strip(),
            is_pinned=request.POST.get('is_pinned') == 'on',
        )
        messages.success(request, 'Announcement posted.')
        return redirect('teacher_classroom_announce', classroom_id=classroom_id)
    return render(request, 'teacher/classroom_announce.html', {
        'classroom': classroom, 'announcements': announcements, 'active_tab': 'announcements',
    })


@role_required('teacher')
def classroom_courses(request, classroom_id):
    classroom = _classroom(request, classroom_id)
    if request.method == 'POST':
        CourseContent.objects.create(
            classroom=classroom,
            title=request.POST.get('title', '').strip(),
            content_type=request.POST.get('content_type', 'note'),
            unit=request.POST.get('unit', '').strip(),
            video_url=request.POST.get('video_url', '').strip(),
            file=request.FILES.get('file'),
        )
        messages.success(request, 'Content added.')
        return redirect('teacher_classroom_courses', classroom_id=classroom_id)
    contents = classroom.course_contents.all()
    units = {}
    for c in contents:
        units.setdefault(c.unit or 'General', []).append(c)
    return render(request, 'teacher/classroom_courses.html', {
        'classroom': classroom, 'units': units, 'active_tab': 'courses',
    })


@role_required('teacher')
def classroom_classwork(request, classroom_id):
    classroom = _classroom(request, classroom_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            Assignment.objects.create(
                classroom=classroom,
                title=request.POST.get('title', '').strip(),
                description=request.POST.get('description', '').strip(),
                due_date=request.POST.get('due_date'),
                max_score=int(request.POST.get('max_score', 20)),
                file=request.FILES.get('file'),
            )
            messages.success(request, 'Assignment created.')
        elif action == 'grade':
            sub = get_object_or_404(Submission, pk=request.POST.get('submission_id'),
                                    assignment__classroom=classroom)
            sub.score    = request.POST.get('score') or None
            sub.feedback = request.POST.get('feedback', '')
            sub.save()
            messages.success(request, 'Grade saved.')
        return redirect('teacher_classroom_classwork', classroom_id=classroom_id)

    assignment_data = [
        {'assignment': a, 'submissions': a.submissions.select_related('student').all()}
        for a in classroom.assignments.all()
    ]
    return render(request, 'teacher/classroom_classwork.html', {
        'classroom': classroom, 'assignment_data': assignment_data, 'active_tab': 'classwork',
    })


@role_required('teacher')
def classroom_peoples(request, classroom_id):
    classroom = _classroom(request, classroom_id)
    if request.method == 'POST':
        classroom.students.remove(request.POST.get('remove_student'))
        messages.success(request, 'Student removed.')
        return redirect('teacher_classroom_peoples', classroom_id=classroom_id)
    return render(request, 'teacher/classroom_peoples.html', {
        'classroom': classroom, 'students': classroom.students.all(), 'active_tab': 'peoples',
    })


@role_required('teacher')
def classroom_grade(request, classroom_id):
    classroom = _classroom(request, classroom_id)
    grade_data = []
    for student in classroom.students.all():
        subs       = Submission.objects.filter(student=student, assignment__classroom=classroom, score__isnull=False)
        total      = sum(s.score for s in subs)
        max_total  = sum(s.assignment.max_score for s in subs)
        grade_data.append({
            'student': student, 'submissions': subs,
            'total_score': total, 'total_max': max_total,
            'percentage': round(total / max_total * 100, 1) if max_total else None,
        })
    return render(request, 'teacher/classroom_grade.html', {
        'classroom': classroom, 'grade_data': grade_data,
        'assignments': classroom.assignments.all(), 'active_tab': 'grades',
    })


@role_required('teacher')
def classroom_chat(request, classroom_id):
    classroom = _classroom(request, classroom_id)
    from chat.models import Message
    # Show all enrolled students in sidebar, not just those who messaged
    all_students = classroom.students.all().order_by('first_name', 'last_name', 'username')
    selected     = None
    chat_messages = []
    sid = request.GET.get('student')
    if sid:
        from accounts.models import User
        selected      = get_object_or_404(User, pk=sid, role='student')
        chat_messages = Message.objects.filter(
            classroom=classroom,
            sender__in=[request.user, selected],
            receiver__in=[request.user, selected],
        ).order_by('created_at')
        chat_messages.filter(receiver=request.user, is_read=False).update(is_read=True)
    # Annotate unread counts per student
    from django.db.models import Count, Q
    unread_counts = {
        row['sender_id']: row['cnt']
        for row in Message.objects.filter(
            classroom=classroom,
            receiver=request.user,
            is_read=False,
        ).values('sender_id').annotate(cnt=Count('id'))
    }
    for student in all_students:
        student.unread = unread_counts.get(student.pk, 0)
    return render(request, 'teacher/classroom_chat.html', {
        'classroom': classroom, 'students_with_chats': all_students,
        'selected_student': selected, 'messages': chat_messages, 'active_tab': 'chat',
    })
