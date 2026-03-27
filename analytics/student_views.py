from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required

from analytics.services.analytics_services import StudentAnalyticsService
from students.views import _student_layout_context


@login_required
@role_required('student')
def student_analytics(request):
    """Student analytics dashboard."""
    service = StudentAnalyticsService(request.user)

    context = {
        'performance_dashboard': service.get_personal_performance_dashboard(),
        'progress_trends': service.get_progress_trends(),
        'assignment_tracking': service.get_assignment_tracking(),
        'strengths_weaknesses': service.get_strengths_and_weaknesses(),
        'class_ranks': service.get_class_rank(),
        **_student_layout_context(request.user, active_nav='analytics'),
    }

    return render(request, 'student/analytics.html', context)
