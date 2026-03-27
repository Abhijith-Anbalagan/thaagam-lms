from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required

from analytics.services.analytics_services import ManagementAnalyticsService


@login_required
@role_required('management')
def management_analytics(request):
    """Management analytics dashboard."""
    service = ManagementAnalyticsService(request.user)

    context = {
        'course_completion': service.get_course_completion_rates(),
        'assignment_analytics': service.get_assignment_submission_analytics(),
        'engagement_metrics': service.get_engagement_metrics(),
        'department_performance': service.get_department_performance(),
    }

    return render(request, 'management/analytics.html', context)