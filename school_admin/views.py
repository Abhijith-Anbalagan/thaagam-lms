from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from accounts.decorators import role_required
from accounts.models import User, Invitation


@role_required('school_admin')
def dashboard(request):
    school      = request.user.school
    teachers    = User.objects.filter(school=school, role='teacher')
    students    = User.objects.filter(school=school, role='student')
    management  = User.objects.filter(school=school, role='management')
    from classrooms.models import Classroom
    from announcements.models import Announcement
    classrooms  = Classroom.objects.filter(school=school)
    announcements = Announcement.objects.filter(school=school).order_by('-created_at')[:5]
    return render(request, 'school_admin/dashboard.html', {
        'school': school, 'teachers': teachers, 'students': students,
        'management': management, 'classrooms': classrooms,
        'announcements': announcements,
        'total_teachers': teachers.count(), 'total_students': students.count(),
        'total_classrooms': classrooms.count(),
    })


@role_required('school_admin')
def invite_management(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            inv = Invitation.objects.create(
                email=email, role='management',
                school=request.user.school, invited_by=request.user,
            )
            url = request.build_absolute_uri(f'/accept-invite/{inv.token}/')
            from django.core.mail import send_mail
            send_mail('EduPlatform Invitation',
                      f'You have been invited as Management.\nAccept: {url}',
                      'noreply@eduplatform.com', [email], fail_silently=True)
            messages.success(request, f'Invitation sent to {email}.')
            return redirect('school_admin_dashboard')
    return render(request, 'school_admin/invite_management.html')


@role_required('school_admin')
def management_list(request):
    school     = request.user.school
    management = User.objects.filter(school=school, role='management')
    return render(request, 'school_admin/management_list.html', {'management': management})


@role_required('school_admin')
def reports(request):
    school = request.user.school
    from classrooms.models import Classroom
    from assignments.models import Submission
    from django.db.models import Avg
    classrooms = Classroom.objects.filter(school=school)
    avg_score  = Submission.objects.filter(
        assignment__classroom__school=school, score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']
    return render(request, 'school_admin/reports.html', {
        'school': school, 'classrooms': classrooms, 'avg_score': avg_score,
    })
