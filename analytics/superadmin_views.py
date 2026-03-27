from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required

from analytics.services.analytics_services import SuperAdminAnalyticsService


@login_required
@role_required('super_admin')
def superadmin_analytics(request):
    """Super Admin analytics dashboard."""
    service = SuperAdminAnalyticsService()

    platform_overview = service.get_platform_overview()
    school_performance = service.get_school_performance()

    # Calculate additional metrics for the existing template
    schools_queryset = school_performance
    active_schools = sum(1 for s in schools_queryset if s.get('is_active', True))
    suspended_schools = len(schools_queryset) - active_schools
    total_students = sum(s.get('student_count', 0) for s in schools_queryset)
    total_teachers = sum(s.get('teacher_count', 0) for s in schools_queryset)
    total_classrooms = sum(s.get('classroom_count', 0) for s in schools_queryset)
    max_students = max((s.get('student_count', 0) for s in schools_queryset), default=0)
    max_teachers = max((s.get('teacher_count', 0) for s in schools_queryset), default=0)

    # Format school_breakdown for the template
    school_breakdown = []
    for school in schools_queryset:
        school_breakdown.append({
            'name': school.get('name', ''),
            'is_active': True,  # Assuming all are active for now
            'sc': school.get('student_count', 0),
            'tc': school.get('teacher_count', 0),
            'cc': school.get('classroom_count', 0),
        })

    context = {
        'platform_overview': platform_overview,
        'school_performance': school_performance,
        'user_growth_trends': service.get_user_growth_trends(),
        'system_usage': service.get_system_usage_analytics(),
        # Variables for existing template compatibility
        'schools': len(schools_queryset),
        'active_schools': active_schools,
        'suspended_schools': suspended_schools,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_classrooms': total_classrooms,
        'school_breakdown': school_breakdown,
        'max_students': max_students,
        'max_teachers': max_teachers,
    }

    return render(request, 'superadmin/analytics.html', context)