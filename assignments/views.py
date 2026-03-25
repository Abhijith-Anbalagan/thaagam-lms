from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from accounts.decorators import role_required
from .models import Assignment, Submission


@role_required('teacher')
def assignment_detail(request, assignment_id):
    assignment = get_object_or_404(
        Assignment, pk=assignment_id, classroom__teacher=request.user
    )
    classroom = assignment.classroom

    # Grade POST handler
    if request.method == 'POST':
        sub_id   = request.POST.get('submission_id')
        score    = request.POST.get('score')
        feedback = request.POST.get('feedback', '')
        if sub_id and score is not None:
            sub          = get_object_or_404(Submission, pk=sub_id, assignment=assignment)
            sub.score    = score
            sub.feedback = feedback
            sub.save()
            messages.success(request, f'Grade saved for {sub.student.get_full_name()}.')
        return redirect('assignment_detail', assignment_id=assignment_id)

    all_students = classroom.students.all()
    sub_map      = {s.student_id: s for s in assignment.submissions.select_related('student')}

    submitted     = []
    not_submitted = []
    late          = []
    resubmitted   = []

    for student in all_students:
        sub = sub_map.get(student.pk)
        if sub is None:
            not_submitted.append(student)
        elif sub.is_late:
            if sub.score is not None:
                resubmitted.append(sub)   # late + already graded = re-reviewed
            else:
                late.append(sub)          # late + not yet graded
        else:
            submitted.append(sub)         # on time

    return render(request, 'teacher/assignment_detail.html', {
        'assignment':    assignment,
        'classroom':     classroom,
        'submitted':     submitted,
        'not_submitted': not_submitted,
        'late':          late,
        'resubmitted':   resubmitted,
        'active_tab':    'classwork',
    })
