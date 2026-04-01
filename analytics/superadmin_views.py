from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from accounts.models import User
from superadmin.models import School
from classrooms.models import Classroom
from analytics.services.analytics_services import SuperAdminAnalyticsService


@login_required
@role_required('super_admin')
def superadmin_analytics(request):
    """Super Admin analytics dashboard."""
    service = SuperAdminAnalyticsService()

    platform_overview  = service.get_platform_overview()
    school_performance = service.get_school_performance()
    schools_queryset   = list(school_performance)  # evaluate once

    # ✅ Direct DB queries — same as dashboard, always accurate
    total_students    = User.objects.filter(role='student').count()
    total_teachers    = User.objects.filter(role='teacher').count()
    total_classrooms  = Classroom.objects.count()
    active_schools    = School.objects.filter(is_active=True).count()
    suspended_schools = School.objects.filter(is_active=False).count()

    max_students = max((s.get('student_count', 0) for s in schools_queryset), default=1) or 1
    max_teachers = max((s.get('teacher_count', 0) for s in schools_queryset), default=1) or 1

    school_breakdown = [
        {
            'id':        s.get('id', ''),
            'name':      s.get('name', ''),
            'is_active': s.get('is_active', True),
            'sc':        s.get('student_count', 0),
            'tc':        s.get('teacher_count', 0),
            'cc':        s.get('classroom_count', 0),
        }
        for s in schools_queryset
    ]

    context = {
        'platform_overview':  platform_overview,
        'school_performance': school_performance,
        'user_growth_trends': service.get_user_growth_trends(),
        'system_usage':       service.get_system_usage_analytics(),
        'schools':            School.objects.count(),
        'active_schools':     active_schools,
        'suspended_schools':  suspended_schools,
        'total_students':     total_students,
        'total_teachers':     total_teachers,
        'total_classrooms':   total_classrooms,
        'school_breakdown':   school_breakdown,
        'max_students':       max_students,
        'max_teachers':       max_teachers,
    }

    return render(request, 'superadmin/analytics.html', context)
