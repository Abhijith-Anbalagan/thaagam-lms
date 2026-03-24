from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from accounts.decorators import role_required
from .models import Announcement


@role_required('management', 'school_admin')
def school_wide_list(request):
    """School-wide announcements management page for management/school_admin."""
    school        = request.user.school
    announcements = Announcement.objects.filter(
        school=school, classroom__isnull=True
    ).select_related('posted_by')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            Announcement.objects.create(
                posted_by  = request.user,
                school     = school,
                classroom  = None,
                title      = request.POST.get('title', '').strip(),
                body       = request.POST.get('body', '').strip(),
                meet_link  = request.POST.get('meet_link', '').strip(),
                target     = request.POST.get('target', 'all'),
                is_pinned  = request.POST.get('is_pinned') == 'on',
            )
            messages.success(request, 'Announcement posted to the whole school.')

        elif action == 'delete':
            ann = get_object_or_404(
                Announcement, pk=request.POST.get('announcement_id'), school=school
            )
            ann.delete()
            messages.success(request, 'Announcement deleted.')

        elif action == 'toggle_pin':
            ann = get_object_or_404(
                Announcement, pk=request.POST.get('announcement_id'), school=school
            )
            ann.is_pinned = not ann.is_pinned
            ann.save(update_fields=['is_pinned'])
            messages.success(
                request,
                'Announcement pinned.' if ann.is_pinned else 'Announcement unpinned.'
            )

        return redirect('announcements_school_wide')

    return render(request, 'announcements/school_wide.html', {
        'announcements': announcements,
    })


@role_required('student')
def student_feed(request):
    """All announcements across all of a student's classrooms in one feed."""
    from classrooms.models import Classroom
    classrooms = Classroom.objects.filter(
        school=request.user.school, students=request.user
    )
    announcements = Announcement.objects.filter(
        Q(classroom__in=classrooms) |
        Q(classroom__isnull=True, school=request.user.school)
    ).filter(
        Q(target='all') | Q(target='students')
    ).select_related('posted_by', 'classroom').order_by('-is_pinned', '-created_at')

    return render(request, 'announcements/feed.html', {
        'announcements': announcements,
        'classrooms':    classrooms,
    })
