# Main analytics views - imports all role-specific views
from accounts.decorators import role_required
from .superadmin_views import superadmin_analytics
from .school_admin_views import school_admin_analytics
from .management_views import management_analytics
from .teacher_views import teacher_analytics, classroom_analytics, export_classroom_analytics, export_overall_analytics
from .student_views import student_analytics, student_assignment_tracking

# Legacy function for backward compatibility
from .teacher_views import teacher_analytics as teacher_analytics_legacy


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
