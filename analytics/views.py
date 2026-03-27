from datetime import timedelta

from django.shortcuts import render
from django.db.models import Avg, Count, Q
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import User
from assignments.models import Assignment, Submission
from chat.models import Message
from announcements.models import Announcement


def _get_user_classrooms(user):
    from classrooms.models import Classroom

    if user.role == 'teacher':
        return Classroom.objects.filter(teacher=user)

    if user.role == 'management':
        teacher_emails = user.sent_invites.filter(role='teacher', accepted=True).values_list('email', flat=True)
        teachers = User.objects.filter(email__in=teacher_emails, role='teacher')
        return Classroom.objects.filter(school=user.school, teacher__in=teachers)

    if user.role == 'school_admin':
        return Classroom.objects.filter(school=user.school)

    # Super admin and fallback: all classrooms
    return Classroom.objects.all()


@role_required('teacher', 'management', 'school_admin', 'super_admin')
def teacher_analytics(request):
    from classrooms.models import Classroom
    classrooms = Classroom.objects.filter(teacher=request.user)
    data = []
    for c in classrooms:
        avg = Submission.objects.filter(
            assignment__classroom=c, score__isnull=False
        ).aggregate(avg=Avg('score'))['avg']
        data.append({
            'classroom':         c,
            'avg_score':         round(avg, 1) if avg else None,
            'total_students':    c.student_count,
            'total_assignments': c.assignments.count(),
            'pending_submissions': c.pending_submission_count,
        })
    return render(request, 'management/analytics.html', {'data': data})


@role_required('school_admin', 'super_admin')
def school_analytics(request):
    from classrooms.models import Classroom
    school = request.user.school
    classrooms = Classroom.objects.filter(school=school)
    avg = Submission.objects.filter(
        assignment__classroom__school=school, score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']
    return render(request, 'school_admin/reports.html', {
        'school': school, 'classrooms': classrooms, 'avg_score': avg,
    })
