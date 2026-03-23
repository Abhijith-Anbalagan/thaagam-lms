from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import role_required
from classrooms.models import Classroom
from .models import Assignment, Submission


@role_required('student')
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    classroom  = assignment.classroom

    # Ensure student is in this classroom
    if not classroom.students.filter(pk=request.user.pk).exists():
        messages.error(request, 'You are not enrolled in this classroom.')
        return redirect('student_dashboard')

    if request.method == 'POST':
        file = request.FILES.get('file')
        if file:
            sub, created = Submission.objects.get_or_create(
                assignment=assignment, student=request.user,
                defaults={'file': file}
            )
            if not created:
                if not assignment.is_overdue:
                    sub.file = file
                    sub.save()
                    messages.success(request, 'Submission updated.')
                else:
                    messages.error(request, 'Deadline has passed — cannot re-submit.')
            else:
                messages.success(request, 'Assignment submitted!')
        return redirect('student_classroom_classwork', class_id=classroom.pk)

    return render(request, 'student/classroom_classwork.html', {
        'assignment': assignment, 'classroom': classroom,
    })
