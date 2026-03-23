from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.decorators import role_required
from accounts.models import User, Invitation


@role_required('management')
def dashboard(request):
    school = request.user.school
    my_invites = request.user.sent_invites.filter(role='teacher', accepted=True).values_list('email', flat=True)
    teachers   = User.objects.filter(email__in=my_invites, role='teacher')
    from classrooms.models import Classroom
    from announcements.models import Announcement
    classrooms    = Classroom.objects.filter(school=school, teacher__in=teachers)
    announcements = Announcement.objects.filter(school=school).order_by('-created_at')[:5]
    return render(request, 'management/dashboard.html', {
        'teachers': teachers, 'classrooms': classrooms,
        'announcements': announcements,
        'total_teachers': teachers.count(), 'total_classrooms': classrooms.count(),
    })


@role_required('management')
def invite_teacher(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            inv = Invitation.objects.create(
                email=email, role='teacher',
                school=request.user.school, invited_by=request.user,
            )
            url = request.build_absolute_uri(f'/accept-invite/{inv.token}/')
            from django.core.mail import send_mail
            send_mail('EduPlatform Teacher Invitation',
                      f'You are invited as a Teacher.\nAccept: {url}',
                      'noreply@eduplatform.com', [email], fail_silently=True)
            messages.success(request, f'Invitation sent to {email}.')
            return redirect('management_dashboard')
    return render(request, 'management/invite_teacher.html')


@role_required('management')
def teachers_list(request):
    my_invites = request.user.sent_invites.filter(role='teacher', accepted=True).values_list('email', flat=True)
    teachers   = User.objects.filter(email__in=my_invites, role='teacher')
    return render(request, 'management/teachers_list.html', {'teachers': teachers})
