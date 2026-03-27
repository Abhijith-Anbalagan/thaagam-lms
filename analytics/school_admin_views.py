from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required

from analytics.services.analytics_services import SchoolAdminAnalyticsService


@login_required
@role_required('school_admin')
def school_admin_analytics(request):
    """School Admin analytics dashboard."""
    service = SchoolAdminAnalyticsService(request.user.school)

    context = {
        'school_metrics': service.get_school_dashboard_metrics(),
        'teacher_performance': service.get_teacher_performance(),
        'classroom_performance': service.get_classroom_performance(),
        'student_progress': service.get_student_progress_overview(),
    }

    return render(request, 'school_admin/analytics.html', context)