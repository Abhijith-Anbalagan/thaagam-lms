from django.shortcuts import render, get_object_or_404
from accounts.decorators import role_required
from assignments.models import Submission
from django.db.models import Avg, Count


@role_required('teacher', 'management', 'school_admin', 'super_admin')
def teacher_analytics(request):
    from classrooms.models import Classroom
    classrooms = Classroom.objects.filter(teacher=request.user)
    data = []
    for c in classrooms:
        avg = Submission.objects.filter(
            assignment__classroom=c, score__isnull=False
        ).aggregate(avg=Avg('score'))['avg']
        data.append({'classroom': c, 'avg_score': avg,
                     'total_students': c.student_count,
                     'total_assignments': c.assignments.count()})
    return render(request, 'management/analytics.html', {'data': data})


@role_required('school_admin', 'super_admin')
def school_analytics(request):
    school = request.user.school
    from classrooms.models import Classroom
    classrooms = Classroom.objects.filter(school=school)
    avg = Submission.objects.filter(
        assignment__classroom__school=school, score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']
    return render(request, 'school_admin/reports.html', {
        'school': school, 'classrooms': classrooms, 'avg_score': avg,
    })
