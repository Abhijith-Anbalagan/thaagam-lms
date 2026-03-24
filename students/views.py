from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import role_required
from classrooms.models import Classroom, CourseContent
from assignments.models import Assignment, Submission
from announcements.models import Announcement
from chat.models import Message
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .forms import JoinClassroomForm, SubmissionForm

@login_required
@role_required('student')
def student_dashboard(request):
    # Rule: Always filter by request.user.school
    classrooms = Classroom.objects.filter(
        school=request.user.school, 
        students=request.user
    ).select_related('teacher', 'school')
    
    # Get recent announcements
    recent_announcements = Announcement.objects.filter(
        Q(classroom__in=classrooms) | Q(classroom__isnull=True, school=request.user.school)
    ).order_by('-created_at')[:5]
    
    # Get pending assignments
    pending_assignments = Assignment.objects.filter(
        classroom__in=classrooms,
        due_date__gte=timezone.now()
    ).exclude(
        submissions__student=request.user
    ).order_by('due_date')[:5]
    
    # Calculate overall stats
    total_submissions = Submission.objects.filter(
        student=request.user,
        assignment__classroom__in=classrooms
    ).count()
    
    graded_submissions = Submission.objects.filter(
        student=request.user,
        assignment__classroom__in=classrooms,
        score__isnull=False
    )
    
    avg_score = graded_submissions.aggregate(Avg('score'))['score__avg'] or 0
    
    context = {
        'classrooms': classrooms,
        'recent_announcements': recent_announcements,
        'pending_assignments': pending_assignments,
        'total_submissions': total_submissions,
        'avg_score': round(avg_score, 1) if avg_score else 0,
    }
    return render(request, 'student/dashboard.html', context)

@login_required
@role_required('student')
def classroom_announce(request, id):
    classroom = get_object_or_404(
        Classroom, 
        id=id, 
        school=request.user.school, 
        students=request.user
    )
    
    # Fetch announcements for this classroom or school-wide
    announcements = Announcement.objects.filter(
        Q(classroom=classroom) | Q(classroom__isnull=True, school=request.user.school)
    ).select_related('posted_by').order_by('-is_pinned', '-created_at')
    
    context = {
        'classroom': classroom,
        'announcements': announcements
    }
    return render(request, 'student/classroom_announce.html', context)

@login_required
@role_required('student')
def classroom_courses(request, id):
    classroom = get_object_or_404(
        Classroom, 
        id=id, 
        school=request.user.school, 
        students=request.user
    )
    
    courses = CourseContent.objects.filter(
        classroom=classroom
    ).order_by('unit', 'created_at')
    
    # Group by unit
    units = {}
    for course in courses:
        unit_name = course.unit or 'General'
        if unit_name not in units:
            units[unit_name] = []
        units[unit_name].append(course)
    
    context = {
        'classroom': classroom,
        'courses': courses,
        'units': units
    }
    return render(request, 'student/classroom_courses.html', context)

@login_required
@role_required('student')
def classroom_classwork(request, id):
    classroom = get_object_or_404(
        Classroom, 
        id=id, 
        school=request.user.school, 
        students=request.user
    )
    
    assignments = Assignment.objects.filter(
        classroom=classroom
    ).order_by('-created_at')
    
    # Get student's submissions for these assignments
    submissions = Submission.objects.filter(
        assignment__classroom=classroom,
        student=request.user
    ).select_related('assignment')
    
    submission_dict = {sub.assignment_id: sub for sub in submissions}
    
    # Attach submission status to each assignment
    for assignment in assignments:
        assignment.student_submission = submission_dict.get(assignment.id)
    
    context = {
        'classroom': classroom,
        'assignments': assignments
    }
    return render(request, 'student/classroom_classwork.html', context)

@login_required
@role_required('student')
def classroom_peoples(request, id):
    classroom = get_object_or_404(
        Classroom, 
        id=id, 
        school=request.user.school, 
        students=request.user
    )
    
    students = classroom.students.all().order_by('first_name', 'last_name', 'username')
    
    context = {
        'classroom': classroom,
        'students': students,
        'teacher': classroom.teacher,
        'total_students': students.count()
    }
    return render(request, 'student/classroom_peoples.html', context)

@login_required
@role_required('student')
def classroom_grades(request, id):
    classroom = get_object_or_404(
        Classroom, 
        id=id, 
        school=request.user.school, 
        students=request.user
    )
    
    submissions = Submission.objects.filter(
        assignment__classroom=classroom,
        student=request.user
    ).select_related('assignment').order_by('-submitted_at')
    
    # Calculate stats
    graded = submissions.filter(score__isnull=False)
    total_score = sum(s.score for s in graded if s.score)
    total_possible = sum(s.assignment.max_score for s in graded)
    
    avg_percentage = round((total_score / total_possible * 100), 1) if total_possible > 0 else 0
    
    context = {
        'classroom': classroom,
        'submissions': submissions,
        'total_submissions': submissions.count(),
        'graded_count': graded.count(),
        'avg_percentage': avg_percentage
    }
    return render(request, 'student/classroom_grades.html', context)

@login_required
@role_required('student')
def classroom_chat(request, id):
    classroom = get_object_or_404(
        Classroom,
        id=id,
        school=request.user.school,
        students=request.user
    )

    teacher = classroom.teacher

    # Load existing messages between this student and the teacher
    chat_messages = Message.objects.filter(
        classroom=classroom,
        sender__in=[request.user, teacher],
        receiver__in=[request.user, teacher],
    ).order_by('created_at')

    # Mark unread messages as read
    chat_messages.filter(receiver=request.user, is_read=False).update(is_read=True)

    context = {
        'classroom': classroom,
        'teacher': teacher,
        'messages': chat_messages,
    }
    return render(request, 'student/classroom_chat.html', context)


@login_required
@role_required('student')
def join_classroom(request):
    if request.method == 'POST':
        form = JoinClassroomForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['class_code']
            try:
                classroom = Classroom.objects.get(
                    code=code,
                    school=request.user.school
                )
                
                # Check if already joined
                if classroom.students.filter(id=request.user.id).exists():
                    messages.warning(request, 'You are already enrolled in this classroom.')
                else:
                    classroom.students.add(request.user)
                    messages.success(request, f'Successfully joined {classroom.name}!')
                    return redirect('students:classroom_announce', id=classroom.id)
                    
            except Classroom.DoesNotExist:
                messages.error(request, 'Invalid class code. Please check and try again.')
    else:
        form = JoinClassroomForm()
    
    return render(request, 'student/join_class.html', {'form': form})


@login_required
@role_required('student')
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(
        Assignment,
        id=assignment_id,
        classroom__school=request.user.school,
        classroom__students=request.user
    )
    
    # Check if already submitted
    existing_submission = Submission.objects.filter(
        assignment=assignment,
        student=request.user
    ).first()
    
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES, instance=existing_submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.save()
            
            if existing_submission:
                messages.success(request, 'Assignment resubmitted successfully!')
            else:
                messages.success(request, 'Assignment submitted successfully!')
            
            return redirect('students:classroom_classwork', id=assignment.classroom.id)
    else:
        form = SubmissionForm(instance=existing_submission)
    
    context = {
        'assignment': assignment,
        'classroom': assignment.classroom,
        'form': form,
        'existing_submission': existing_submission
    }
    return render(request, 'student/submit_assignment.html', context)