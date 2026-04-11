from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta
from accounts.decorators import role_required
import openpyxl
from openpyxl.styles import Font, PatternFill

from analytics.services.analytics_services import ManagementAnalyticsService
from classrooms.models import Classroom
from assignments.models import Assignment, Submission


@login_required
@role_required('management')
def management_analytics_excel(request):
    """Download analytics data as Excel."""
    service = ManagementAnalyticsService(request.user)

    # Create workbook
    wb = openpyxl.Workbook()
    
    # Classroom Performance Sheet
    ws1 = wb.active
    ws1.title = "Classroom Performance"
    ws1.append(["Classroom", "Students", "Avg Score", "Submission Rate"])
    for c in service.get_department_performance():
        ws1.append([c['name'], c['student_count'], c['avg_score'], c['submission_rate']])
    
    # Assignment Analytics Sheet
    ws2 = wb.create_sheet("Assignment Analytics")
    ws2.append(["Assignment", "Students", "Submissions", "Submission Rate", "Late Submissions"])
    for a in service.get_assignment_submission_analytics():
        ws2.append([a['title'], a['total_students'], a['submissions_count'], a['submission_rate'], a['late_submissions']])
    
    # Course Completion Sheet
    ws3 = wb.create_sheet("Course Completion")
    ws3.append(["Classroom", "Assignments", "Completed", "Completion Rate"])
    for c in service.get_course_completion_rates():
        ws3.append([c['name'], c['total_assignments'], c['completed_submissions'], c['completion_rate']])
    
    # Style headers
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4c68d7", end_color="4c68d7", fill_type="solid")
    for ws in [ws1, ws2, ws3]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
    
    # Response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=analytics.xlsx'
    wb.save(response)
    return response



@login_required
@role_required('management')
def management_analytics(request):
    """
    Management-level analytics view.
    Accessible by school admins / management role only.
    Filters all data by the logged-in user's school.
    """
    school = request.user.school_id  # school FK on User

    # ── 1. Base querysets scoped to this school ──────────────────────────
    classrooms = Classroom.objects.filter(school_id=school)

    # ── 2. Per-classroom stats ────────────────────────────────────────────
    now = timezone.now()
    one_month_ago = now - timedelta(days=30)
    two_months_ago = now - timedelta(days=60)

    data = []
    for classroom in classrooms:

        # Students enrolled in this classroom
        total_students = classroom.students.count()  # reverse M2M

        # Assignments in this classroom
        assignments = Assignment.objects.filter(classroom=classroom)
        total_assignments = assignments.count()

        # All submissions for this classroom's assignments
        submissions = Submission.objects.filter(
            assignment__classroom=classroom
        )

        # Avg score — only graded submissions (score is not None)
        graded_submissions = submissions.filter(score__isnull=False)
        avg_score_data = graded_submissions.aggregate(avg=Avg('score'))
        raw_avg = avg_score_data['avg']

        # Normalise score to percentage using max_score
        # We calculate weighted avg: sum(score/max_score * 100) / count
        avg_score = None
        if raw_avg is not None and total_assignments > 0:
            # Compute percentage per submission then average
            scores_pct = []
            for sub in graded_submissions.select_related('assignment'):
                max_s = sub.assignment.max_score or 100
                scores_pct.append((sub.score / max_s) * 100)
            if scores_pct:
                avg_score = round(sum(scores_pct) / len(scores_pct), 1)

        # Submission rate: submitted / (students × assignments) × 100
        expected = total_students * total_assignments
        submission_rate = None
        if expected > 0:
            submission_rate = round((submissions.count() / expected) * 100, 1)
            submission_rate = min(submission_rate, 100.0)  # cap at 100

        # Trend: compare avg score this month vs last month
        trend = None
        this_month_subs = graded_submissions.filter(
            submitted_at__gte=one_month_ago
        )
        last_month_subs = graded_submissions.filter(
            submitted_at__gte=two_months_ago,
            submitted_at__lt=one_month_ago
        )

        def pct_avg(qs):
            vals = []
            for sub in qs.select_related('assignment'):
                max_s = sub.assignment.max_score or 100
                vals.append((sub.score / max_s) * 100)
            return round(sum(vals) / len(vals), 1) if vals else None

        this_avg = pct_avg(this_month_subs)
        last_avg = pct_avg(last_month_subs)
        if this_avg is not None and last_avg is not None:
            trend = round(this_avg - last_avg, 1)

        data.append({
            'classroom': classroom,
            'total_students': total_students,
            'total_assignments': total_assignments,
            'avg_score': avg_score,
            'submission_rate': submission_rate,
            'trend': trend,
        })

    # ── 3. Summary stats ─────────────────────────────────────────────────
    total_students = sum(d['total_students'] for d in data)
    total_assignments = sum(d['total_assignments'] for d in data)

    scored = [d['avg_score'] for d in data if d['avg_score'] is not None]
    overall_avg = round(sum(scored) / len(scored), 1) if scored else None

    # ── 4. Alerts ─────────────────────────────────────────────────────────
    alerts = []

    for d in data:
        name = d['classroom'].name

        # Declining trend alert
        if d['trend'] is not None and d['trend'] <= -5:
            alerts.append({
                'type': 'warning',
                'dot': 'amber',
                'message': f'{name} average score dropped {abs(d["trend"])}% this month — review assignment difficulty.',
                'badge_color': 'amber',
                'badge_label': 'Declining',
            })

        # At-risk students: 3+ consecutive submissions below 40%
        for classroom_data in [d]:
            classroom_obj = classroom_data['classroom']
            students = classroom_obj.students.all()
            at_risk_count = 0
            for student in students:
                recent_subs = Submission.objects.filter(
                    assignment__classroom=classroom_obj,
                    student=student,
                    score__isnull=False,
                ).order_by('-submitted_at')[:3].select_related('assignment')

                sub_list = list(recent_subs)
                if len(sub_list) == 3:
                    all_low = all(
                        (s.score / (s.assignment.max_score or 100)) * 100 < 40
                        for s in sub_list
                    )
                    if all_low:
                        at_risk_count += 1

            if at_risk_count > 0:
                alerts.append({
                    'type': 'danger',
                    'dot': 'red',
                    'message': f'{at_risk_count} student{"s" if at_risk_count > 1 else ""} in {name} scored below 40% on 3+ consecutive assignments.',
                    'badge_color': 'red',
                    'badge_label': 'At Risk',
                })

        # Improving submission rate
        if d['trend'] is not None and d['trend'] >= 5:
            alerts.append({
                'type': 'success',
                'dot': 'green',
                'message': f'{name} average score improved by {d["trend"]}% this month — great progress!',
                'badge_color': 'green',
                'badge_label': 'Improving',
            })

    # ── 5. Chart data ─────────────────────────────────────────────────────

    # Bar chart: classroom labels + avg scores
    bar_labels = [d['classroom'].name for d in data]
    bar_data   = [d['avg_score'] if d['avg_score'] is not None else 0 for d in data]

    # Line chart: monthly submission counts for last 6 months
    line_labels = []
    line_data   = []
    for i in range(5, -1, -1):
        month_start = now - timedelta(days=30 * (i + 1))
        month_end   = now - timedelta(days=30 * i)
        label = month_start.strftime('%b')
        line_labels.append(label)

        all_assignments = Assignment.objects.filter(
            classroom__school_id=school,
            created_at__gte=month_start,
            created_at__lt=month_end,
        )
        total_exp = sum(
            a.classroom.students.count()
            for a in all_assignments
        )
        subs_count = Submission.objects.filter(
            assignment__classroom__school_id=school,
            submitted_at__gte=month_start,
            submitted_at__lt=month_end,
        ).count()

        rate = round((subs_count / total_exp) * 100, 1) if total_exp > 0 else 0
        line_data.append(min(rate, 100))

    # Doughnut: grade distribution across all classrooms
    good_count = sum(1 for d in data if d['avg_score'] and d['avg_score'] >= 70)
    avg_count  = sum(1 for d in data if d['avg_score'] and 50 <= d['avg_score'] < 70)
    low_count  = sum(1 for d in data if d['avg_score'] and d['avg_score'] < 50)
    total_with_data = good_count + avg_count + low_count

    def pct(n):
        return round((n / total_with_data) * 100) if total_with_data > 0 else 0

    donut_labels = ['Good (≥70%)', 'Average (50–70%)', 'Needs Attention (<50%)']
    donut_data   = [pct(good_count), pct(avg_count), pct(low_count)]

    # Histogram: score distribution buckets
    all_graded_subs = Submission.objects.filter(
        assignment__classroom__school_id=school,
        score__isnull=False,
    ).select_related('assignment')

    buckets = [0, 0, 0, 0, 0]  # 0-20, 21-40, 41-60, 61-80, 81-100
    for sub in all_graded_subs:
        max_s = sub.assignment.max_score or 100
        pct_score = (sub.score / max_s) * 100
        if pct_score <= 20:
            buckets[0] += 1
        elif pct_score <= 40:
            buckets[1] += 1
        elif pct_score <= 60:
            buckets[2] += 1
        elif pct_score <= 80:
            buckets[3] += 1
        else:
            buckets[4] += 1

    chart_data = {
        'classroom_performance': {
            'labels': bar_labels,
            'data':   bar_data,
        },
        'assignment_submissions': {
            'labels': line_labels,
            'data':   line_data,
        },
        'grade_distribution': {
            'labels': donut_labels,
            'data':   donut_data,
        },
        'score_distribution': {
            'labels': ['0–20%', '21–40%', '41–60%', '61–80%', '81–100%'],
            'data':   buckets,
        },
    }

    # ── 6. Render ─────────────────────────────────────────────────────────
    context = {
        'data':              data,
        'total_students':    total_students,
        'total_assignments': total_assignments,
        'overall_avg':       overall_avg,
        'alerts':            alerts,
        'chart_data':        chart_data,
    }
    return render(request, 'management/analytics.html', context)