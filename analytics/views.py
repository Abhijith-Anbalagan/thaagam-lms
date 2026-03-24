from django.shortcuts import render
from accounts.decorators import role_required
from assignments.models import Submission
from classrooms.models import Classroom
from django.db.models import Avg, Count, Sum
import json


@role_required('student')
def student_analytics(request):
    classrooms = Classroom.objects.filter(
        school=request.user.school, students=request.user
    ).prefetch_related('assignments')

    submissions = Submission.objects.filter(
        student=request.user,
        assignment__classroom__school=request.user.school,
    ).select_related('assignment', 'assignment__classroom')

    # Per-classroom breakdown
    classroom_data = []
    for c in classrooms:
        subs = [s for s in submissions if s.assignment.classroom_id == c.id]
        graded = [s for s in subs if s.score is not None]
        total_score   = sum(s.score for s in graded)
        total_possible = sum(s.assignment.max_score for s in graded)
        classroom_data.append({
            'classroom':        c,
            'total_assignments': c.assignments.count(),
            'submitted':        len(subs),
            'graded':           len(graded),
            'avg_pct':          round(total_score / total_possible * 100, 1) if total_possible else None,
        })

    # Chart data — graded submissions over time
    graded_subs = sorted(
        [s for s in submissions if s.score is not None],
        key=lambda s: s.submitted_at
    )
    chart_labels = json.dumps([s.assignment.title for s in graded_subs])
    chart_scores = json.dumps([s.score for s in graded_subs])
    chart_max    = json.dumps([s.assignment.max_score for s in graded_subs])

    # Overall stats
    total_graded   = len(graded_subs)
    total_score    = sum(s.score for s in graded_subs)
    total_possible = sum(s.assignment.max_score for s in graded_subs)
    overall_pct    = round(total_score / total_possible * 100, 1) if total_possible else None

    return render(request, 'analytics/student.html', {
        'classroom_data':  classroom_data,
        'total_submitted': submissions.count(),
        'total_graded':    total_graded,
        'overall_pct':     overall_pct,
        'chart_labels':    chart_labels,
        'chart_scores':    chart_scores,
        'chart_max':       chart_max,
    })


@role_required('teacher')
def teacher_analytics(request):
    classrooms = Classroom.objects.filter(
        teacher=request.user
    ).prefetch_related('assignments', 'students')

    classroom_data = []
    for c in classrooms:
        subs   = Submission.objects.filter(assignment__classroom=c, score__isnull=False)
        avg    = subs.aggregate(avg=Avg('score'))['avg']
        top    = subs.order_by('-score').select_related('student').first()
        classroom_data.append({
            'classroom':         c,
            'total_students':    c.student_count,
            'total_assignments': c.assignments.count(),
            'total_submissions': Submission.objects.filter(assignment__classroom=c).count(),
            'pending_grading':   Submission.objects.filter(assignment__classroom=c, score__isnull=True).count(),
            'avg_score':         round(avg, 1) if avg else None,
            'top_student':       top.student if top else None,
        })

    # Chart — avg score per classroom
    chart_labels = json.dumps([d['classroom'].name for d in classroom_data])
    chart_scores = json.dumps([d['avg_score'] or 0 for d in classroom_data])

    return render(request, 'analytics/teacher.html', {
        'classroom_data': classroom_data,
        'total_classrooms': len(classroom_data),
        'total_students':   sum(d['total_students'] for d in classroom_data),
        'total_pending':    sum(d['pending_grading'] for d in classroom_data),
        'chart_labels':     chart_labels,
        'chart_scores':     chart_scores,
    })


@role_required('school_admin', 'management')
def school_analytics(request):
    school     = request.user.school
    classrooms = Classroom.objects.filter(school=school).select_related('teacher')

    classroom_data = []
    for c in classrooms:
        subs = Submission.objects.filter(assignment__classroom=c, score__isnull=False)
        avg  = subs.aggregate(avg=Avg('score'))['avg']
        classroom_data.append({
            'classroom':         c,
            'total_students':    c.student_count,
            'total_assignments': c.assignments.count(),
            'avg_score':         round(avg, 1) if avg else None,
        })

    overall_avg = Submission.objects.filter(
        assignment__classroom__school=school, score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']

    from accounts.models import User
    total_teachers = User.objects.filter(school=school, role='teacher').count()
    total_students = User.objects.filter(school=school, role='student').count()

    chart_labels = json.dumps([d['classroom'].name for d in classroom_data])
    chart_scores = json.dumps([d['avg_score'] or 0 for d in classroom_data])

    return render(request, 'analytics/school.html', {
        'school':           school,
        'classroom_data':   classroom_data,
        'overall_avg':      round(overall_avg, 1) if overall_avg else None,
        'total_teachers':   total_teachers,
        'total_students':   total_students,
        'total_classrooms': classrooms.count(),
        'chart_labels':     chart_labels,
        'chart_scores':     chart_scores,
    })
