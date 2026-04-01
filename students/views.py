from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
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


def _student_layout_context(request, classroom=None, active_nav=None):
    user = request.user
    classrooms = user.joined_classrooms.select_related('teacher', 'school').all()
    nav_classroom = classroom or classrooms.first()

    def parse_session_time(key, default_time):
        raw = request.session.get(key)
        if not raw:
            return default_time
        try:
            dt = timezone.datetime.fromisoformat(raw)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            return dt
        except Exception:
            return default_time

    baseline = user.last_login or timezone.make_aware(datetime.min)
    last_seen_announce = parse_session_time('student_last_seen_announcements', baseline)
    last_seen_assignment = parse_session_time('student_last_seen_assignments', baseline)

    # Track graded submissions per session, not by timestamp
    # (since we can't know exactly when teacher applied the grade)
    seen_graded_submission_ids = request.session.get('student_seen_graded_submission_ids', [])
    graded_submissions = Submission.objects.filter(student=user, score__isnull=False)
    new_graded_submissions = graded_submissions.exclude(id__in=seen_graded_submission_ids)

    new_grades_count = new_graded_submissions.count()
    new_grades_classroom = None
    if new_graded_submissions.exists():
        # Find the classroom of the first new graded submission
        first_new_grade = new_graded_submissions.select_related('assignment__classroom').first()
        new_grades_classroom = first_new_grade.assignment.classroom

    unread_messages = Message.objects.filter(receiver=user, is_read=False).count()
    new_announcements = Announcement.objects.filter(classroom__in=classrooms, created_at__gt=last_seen_announce).count()
    new_assignments = Assignment.objects.filter(classroom__in=classrooms, created_at__gt=last_seen_assignment).count()

    has_updates = unread_messages > 0 or new_announcements > 0 or new_assignments > 0 or new_grades_count > 0

    bell_url = reverse('student_dashboard')
    grades_url = None
    if unread_messages > 0 and nav_classroom:
        bell_url = reverse('student_classroom_chat', args=[nav_classroom.id])
    elif new_announcements > 0 and nav_classroom:
        bell_url = reverse('student_classroom_announce', args=[nav_classroom.id])
    elif new_assignments > 0 and nav_classroom:
        bell_url = reverse('student_classroom_classwork', args=[nav_classroom.id])
    elif new_grades_classroom:
        bell_url = reverse('student_classroom_grade', args=[new_grades_classroom.id])

    if new_grades_classroom:
        grades_url = reverse('student_classroom_grade', args=[new_grades_classroom.id])
    elif nav_classroom:
        grades_url = reverse('student_classroom_grade', args=[nav_classroom.id])

    return {
        'classrooms': classrooms,
        'nav_classroom': nav_classroom,
        'unread_count': unread_messages,
        'new_announcements_count': new_announcements,
        'new_assignments_count': new_assignments,
        'new_grades_count': new_grades_count,
        'has_updates': has_updates,
        'bell_redirect_url': bell_url,
        'new_grades_redirect_url': grades_url,
        'active_nav': active_nav,
    }


@role_required('student')
def dashboard(request):
    classrooms    = request.user.joined_classrooms.select_related('teacher', 'school').all()
    classroom     = classrooms.first()

    if not classroom:
        return redirect('student_join_class')
    pending       = []
    graded_count  = 0

    for c in classrooms:
        for a in c.assignments.filter(due_date__gte=timezone.now()):
            if not Submission.objects.filter(assignment=a, student=request.user).exists():
                pending.append(a)
    
    # Get graded assignments count
    graded_count = Submission.objects.filter(
        student=request.user,
        score__isnull=False
    ).count()

    # Get total course contents count across all classrooms
    total_courses = CourseContent.objects.filter(
        classroom__in=classrooms
    ).count()
    
    # Add enrolled GlobalCourses count (only for courses still assigned to student's classrooms)
    from superadmin.models import CourseEnrollment, ClassroomCourseAssignment
    enrolled_courses_count = CourseEnrollment.objects.filter(
        user=request.user,
        course__classroom_assignments__classroom__in=classrooms
    ).distinct().count()
    
    total_courses += enrolled_courses_count

    recent_announcements = Announcement.objects.filter(
        classroom__in=classrooms
    ).order_by('-created_at')[:6]

    context = {
        'classrooms':            classrooms,
        'classroom':             classroom,
        'nav_classroom':         classroom,
        'pending_assignments':   pending,
        'recent_announcements':  recent_announcements,
        'graded_assignments':    graded_count,
        'total_courses':         total_courses,
        'active_tab':            'dashboard',
        **_student_layout_context(request, classroom=classroom, active_nav='dashboard'),
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
    context = {'error': error, **_student_layout_context(request, active_nav='join_class')}
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
    request.session['student_last_seen_announcements'] = timezone.now().isoformat()
    context = {
        'classroom': classroom, 'announcements': announcements, 'active_tab': 'announcements',
        **_student_layout_context(request, classroom=classroom, active_nav='announcements'),
    }
    return render(request, 'student/classroom_announce.html', context)


@role_required('student')
def classroom_courses(request, class_id):
    classroom = _get_classroom(request, class_id)
    contents  = classroom.course_contents.all()
    units = {}
    for c in contents:
        units.setdefault(c.unit or 'General', []).append(c)
    
    # Get assigned GlobalCourses for this classroom
    from superadmin.models import ClassroomCourseAssignment, GlobalCourse, CourseEnrollment
    assigned_courses = GlobalCourse.objects.filter(
        classroom_assignments__classroom=classroom
    ).select_related('created_by').prefetch_related('concepts')
    
    # Check which courses the student is already enrolled in
    enrolled_course_ids = set(CourseEnrollment.objects.filter(
        user=request.user,
        course__in=assigned_courses
    ).values_list('course_id', flat=True))
    
    context = {
        'classroom': classroom, 'units': units, 'active_tab': 'courses',
        'assigned_courses': assigned_courses,
        'enrolled_course_ids': enrolled_course_ids,
        **_student_layout_context(request, classroom=classroom, active_nav='courses'),
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

    request.session['student_last_seen_assignments'] = timezone.now().isoformat()
    assignment_data = []
    for a in classroom.assignments.all():
        try:    sub = Submission.objects.get(assignment=a, student=request.user)
        except: sub = None
        assignment_data.append({'assignment': a, 'submission': sub})

    context = {
        'classroom': classroom, 'assignment_data': assignment_data, 'active_tab': 'classwork',
        **_student_layout_context(request, classroom=classroom, active_nav='classwork'),
    }
    return render(request, 'student/classroom_classwork.html', context)


@role_required('student')
def classroom_peoples(request, class_id):
    classroom = _get_classroom(request, class_id)
    context = {
        'classroom': classroom, 'students': classroom.students.all(), 'active_tab': 'peoples',
        'student_data': [], # Placeholder, actual data would be fetched here if needed
        **_student_layout_context(request, classroom=classroom, active_nav='peoples'),
    }
    return render(request, 'student/classroom_peoples.html', context)


@role_required('student')
def classroom_grade(request, class_id):
    classroom   = _get_classroom(request, class_id)
    graded_submission_ids = list(
        Submission.objects.filter(student=request.user, score__isnull=False).values_list('id', flat=True)
    )
    request.session['student_seen_graded_submission_ids'] = graded_submission_ids
    grade_data  = []
    total_score = total_max = 0

    # Get assignments ordered by due_date descending (latest first)
    for a in classroom.assignments.all().order_by('-due_date'):
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
        **_student_layout_context(request, classroom=classroom, active_nav='grades'),
    }
    return render(request, 'student/classroom_grade.html', context)


@role_required('student')
def classroom_chat(request, class_id):
    classroom = _get_classroom(request, class_id)

    # All classrooms the student is in (for multi-classroom teacher list)
    all_classrooms = request.user.joined_classrooms.select_related('teacher').all()

    # Build teacher list — one per classroom, deduplicated by teacher pk
    seen = set()
    teachers = []
    for c in all_classrooms:
        t = c.teacher
        if t.pk not in seen:
            seen.add(t.pk)
            teachers.append({'teacher': t, 'classroom': c})

    # Selected teacher — from ?teacher= param or default to current classroom's teacher
    selected_teacher_id = request.GET.get('teacher')
    selected_entry = None
    if selected_teacher_id:
        for entry in teachers:
            if str(entry['teacher'].pk) == str(selected_teacher_id):
                selected_entry = entry
                break
    if not selected_entry and teachers:
        selected_entry = next(
            (e for e in teachers if e['classroom'].pk == classroom.pk),
            teachers[0]
        )

    teacher          = selected_entry['teacher'] if selected_entry else classroom.teacher
    chat_classroom   = selected_entry['classroom'] if selected_entry else classroom

    msgs = Message.objects.filter(
        classroom=chat_classroom,
        sender__in=[request.user, teacher],
        receiver__in=[request.user, teacher],
    ).order_by('created_at')
    msgs.filter(receiver=request.user, is_read=False).update(is_read=True)
    request.session['student_last_seen_messages'] = timezone.now().isoformat()

    from django.core.cache import cache
    from django.contrib.sessions.models import Session

    cached = cache.get(f'user_online_{teacher.pk}')
    if cached is None:
        active_ids = set()
        for s in Session.objects.filter(expire_date__gt=timezone.now()):
            try:
                uid = s.get_decoded().get('_auth_user_id')
                if uid:
                    active_ids.add(int(uid))
            except Exception:
                pass
        teacher_online = teacher.pk in active_ids
        if teacher_online:
            cache.set(f'user_online_{teacher.pk}', True, timeout=None)
    else:
        teacher_online = cached is True

    context = {
        'classroom':        chat_classroom,
        'teacher':          teacher,
        'teacher_online':   teacher_online,
        'chat_messages':    msgs,
        'teachers':         teachers,
        'selected_teacher': teacher,
        'active_tab':       'chat',
        **_student_layout_context(request, classroom=classroom, active_nav='chat'),
    }
    return render(request, 'student/classroom_chat.html', context)


@role_required('student')
def unread_count_api(request):
    """JSON endpoint — returns unread message count for the logged-in student."""
    count = Message.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({'unread': count})


@role_required('student')
def pending_count_api(request):
    """JSON endpoint — returns pending assignments count."""
    classrooms = request.user.joined_classrooms.all()
    count = 0
    for classroom in classrooms:
        for assignment in classroom.assignments.filter(due_date__gte=timezone.now()):
            if not Submission.objects.filter(assignment=assignment, student=request.user).exists():
                count += 1
    return JsonResponse({'pending': count})


@role_required('student')
def graded_count_api(request):
    """JSON endpoint — returns graded assignments count."""
    count = Submission.objects.filter(
        student=request.user,
        score__isnull=False
    ).count()
    return JsonResponse({'graded': count})


@role_required('student')
def course_count_api(request):
    """JSON endpoint — returns total course contents count."""
    classrooms = request.user.joined_classrooms.all()
    count = CourseContent.objects.filter(classroom__in=classrooms).count()
    
    # Add enrolled GlobalCourses count (only for courses still assigned to student's classrooms)
    from superadmin.models import CourseEnrollment
    enrolled_count = CourseEnrollment.objects.filter(
        user=request.user,
        course__classroom_assignments__classroom__in=classrooms
    ).distinct().count()
    count += enrolled_count
    
    return JsonResponse({'courses': count})


@role_required('student')
def course_enroll(request, course_id):
    from superadmin.models import GlobalCourse, CourseEnrollment
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Course enrollment attempt: user={request.user.id}, course_id={course_id}, method={request.method}")

    if request.method != 'POST':
        logger.warning(f"Invalid method: {request.method}")
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Check if the course is assigned to one of the student's classrooms
    classrooms = request.user.joined_classrooms.all()
    logger.info(f"User classrooms: {[c.id for c in classrooms]}")
    
    try:
        course = GlobalCourse.objects.get(
            pk=course_id,
            classroom_assignments__classroom__in=classrooms
        )
        logger.info(f"Found course: {course.title}")
    except GlobalCourse.DoesNotExist:
        logger.error(f"Course {course_id} not found or not assigned to user's classrooms")
        return JsonResponse({'error': 'Course not found or not assigned to your classroom'}, status=404)

    enrollment, created = CourseEnrollment.objects.get_or_create(
        user=request.user, course=course
    )
    
    if created:
        logger.info(f"Created new enrollment for course {course.title}")
        return JsonResponse({
            'enrolled': True,
            'new_enrollment': True,
            'message': f'Successfully enrolled in {course.title}',
            'course_url': f'/student/my-learning/{course.pk}/',
        })
    else:
        logger.info(f"User already enrolled in course {course.title}")
        return JsonResponse({
            'enrolled': True,
            'new_enrollment': False,
            'course_url': f'/student/my-learning/{course.pk}/',
        })


# Apply csrf_exempt decorator
from django.views.decorators.csrf import csrf_exempt
course_enroll = csrf_exempt(course_enroll)


@role_required('student')
def my_learning(request):
    from superadmin.models import CourseEnrollment, GlobalCourse
    
    enrollments = CourseEnrollment.objects.filter(
        user=request.user
    ).select_related('course').prefetch_related('course__concepts')
    
    context = {
        'enrollments': enrollments,
        'active_tab': 'my_learning',
        **_student_layout_context(request, active_nav='my_learning'),
    }
    return render(request, 'student/my_learning.html', context)


@role_required('student')
def course_detail(request, course_id):
    from superadmin.models import GlobalCourse, CourseEnrollment
    
    # Check if student is enrolled in this course
    enrollment = get_object_or_404(
        CourseEnrollment,
        user=request.user,
        course_id=course_id
    )
    
    course = enrollment.course
    concepts = course.concepts.all().prefetch_related('videos')
    
    context = {
        'course': course,
        'concepts': concepts,
        'enrollment': enrollment,
        'active_tab': 'my_learning',
        **_student_layout_context(request, active_nav='my_learning'),
    }
    return render(request, 'student/course_detail.html', context)
