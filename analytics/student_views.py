from django.shortcuts import render
from django.http import JsonResponse
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
        **_student_layout_context(request, active_nav='analytics'),
    }

    return render(request, 'student/analytics.html', context)


@login_required
@role_required('student')
def student_assignment_tracking(request):
    month = request.GET.get('month')
    service = StudentAnalyticsService(request.user)
    assignments = service.get_assignment_tracking(month=month)

    serialized = []
    for item in assignments:
        serialized.append({
            'id': item['id'],
            'title': item['title'],
            'due_date': item['due_date'].strftime('%Y-%m-%d') if item['due_date'] else '',
            'status': 'Submitted' if item['submitted'] else 'Pending',
            'score': f"{item['score']}/{item['max_score']}" if item['score'] is not None else '-',
            'submitted_at': item['submitted_at'].strftime('%Y-%m-%d %H:%M') if item['submitted_at'] else '-',
            'is_late': bool(item['is_late']),
        })

    return JsonResponse({'assignments': serialized})
