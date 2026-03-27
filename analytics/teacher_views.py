from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required

from analytics.services.analytics_services import TeacherAnalyticsService


@login_required
@role_required('teacher', 'management', 'school_admin', 'super_admin')
def teacher_analytics(request):
    """Teacher analytics dashboard."""
    service = TeacherAnalyticsService(request.user)

    context = {
        'class_performance': service.get_class_performance(),
        'student_performance': service.get_student_wise_performance(),
        'assignment_analytics': service.get_assignment_analytics(),
        'weak_students': service.identify_weak_students(),
    }

    return render(request, 'teacher/analytics.html', context)