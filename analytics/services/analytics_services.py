from django.db.models import Avg, Count, Q, Sum, F, Case, When, IntegerField, Max, Min
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from superadmin.models import School
from classrooms.models import Classroom
from assignments.models import Assignment, Submission
from chat.models import Message
from announcements.models import Announcement


class BaseAnalyticsService:
    """Base class for analytics services with common methods."""

    @staticmethod
    def get_date_range(months=6):
        """Get date range for trend analysis."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=months*30)
        return start_date, end_date

    @staticmethod
    def get_user_growth_trend(queryset, months=6):
        """Get user growth trend over time."""
        start_date, end_date = BaseAnalyticsService.get_date_range(months)

        return queryset.filter(
            date_joined__gte=start_date,
            date_joined__lte=end_date
        ).annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

    @staticmethod
    def get_activity_trend(queryset, date_field, months=6):
        """Get activity trend over time."""
        start_date, end_date = BaseAnalyticsService.get_date_range(months)

        return queryset.filter(
            **{f'{date_field}__gte': start_date},
            **{f'{date_field}__lte': end_date}
        ).annotate(
            month=TruncMonth(date_field)
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')


class SuperAdminAnalyticsService(BaseAnalyticsService):
    """Analytics service for Super Admin dashboard."""

    @staticmethod
    def get_platform_overview():
        """Get overall platform statistics."""
        return {
            'total_users': User.objects.count(),
            'total_schools': School.objects.count(),
            'total_classrooms': Classroom.objects.count(),
            'total_assignments': Assignment.objects.count(),
            'total_submissions': Submission.objects.count(),
            'active_users_last_30_days': User.objects.filter(
                last_login__gte=timezone.now() - timedelta(days=30)
            ).count(),
        }

    @staticmethod
    def get_school_performance():
        """Compare performance across schools."""
        return School.objects.annotate(
            student_count=Count('users', filter=Q(users__role='student')),
            teacher_count=Count('users', filter=Q(users__role='teacher')),
            classroom_count=Count('classrooms'),
            avg_submission_rate=Avg(
                Submission.objects.filter(
                    assignment__classroom__school=F('id')
                ).values('assignment__classroom__school').annotate(
                    rate=Count('id') * 100.0 / Count('assignment__classroom__students', distinct=True)
                ).values('rate')
            )
        ).values(
            'id', 'name', 'student_count', 'teacher_count',
            'classroom_count', 'avg_submission_rate'
        )

    @staticmethod
    def get_user_growth_trends():
        """Get user registration trends by role."""
        trends = {}
        roles = ['student', 'teacher', 'school_admin', 'management']

        for role in roles:
            trends[role] = BaseAnalyticsService.get_user_growth_trend(
                User.objects.filter(role=role)
            )

        return trends

    @staticmethod
    def get_system_usage_analytics():
        """Get system usage statistics."""
        last_30_days = timezone.now() - timedelta(days=30)

        return {
            'messages_sent': Message.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            'announcements_created': Announcement.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            'assignments_created': Assignment.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            'submissions_made': Submission.objects.filter(
                submitted_at__gte=last_30_days
            ).count(),
        }


class SchoolAdminAnalyticsService(BaseAnalyticsService):
    """Analytics service for School Admin dashboard."""

    def __init__(self, school):
        self.school = school

    def get_school_dashboard_metrics(self):
        """Get key metrics for the school."""
        return {
            'total_students': self.school.users.filter(role='student').count(),
            'total_teachers': self.school.users.filter(role='teacher').count(),
            'total_classrooms': self.school.classrooms.count(),
            'total_assignments': Assignment.objects.filter(
                classroom__school=self.school
            ).count(),
            'avg_classroom_performance': self._get_avg_classroom_performance(),
        }

    def get_teacher_performance(self):
        """Get performance metrics for teachers in the school."""
        return User.objects.filter(
            role='teacher', school=self.school
        ).annotate(
            classroom_count=Count('classrooms'),
            student_count=Count('classrooms__students', distinct=True),
            avg_student_score=Avg(
                Submission.objects.filter(
                    assignment__classroom__teacher=F('id'),
                    score__isnull=False
                ).values('score')
            )
        ).values(
            'id', 'username', 'email', 'classroom_count',
            'student_count', 'avg_student_score'
        )

    def get_classroom_performance(self):
        """Get performance metrics for classrooms in the school."""
        return Classroom.objects.filter(school=self.school).annotate(
            total_students_count=Count('students'),
            assignment_count=Count('assignments'),
            submission_count=Count('assignments__submissions'),
            avg_score=Avg('assignments__submissions__score'),
            submission_rate=Case(
                When(student_count=0, then=0),
                default=Count('assignments__submissions') * 100.0 / (Count('assignments') * Count('students')),
                output_field=IntegerField()
            )
        ).values(
            'id', 'name', 'code', 'student_count', 'assignment_count',
            'submission_count', 'avg_score', 'submission_rate'
        )

    def get_student_progress_overview(self):
        """Get overall student progress in the school."""
        return User.objects.filter(
            role='student', school=self.school
        ).annotate(
            assignment_count=Count('submissions__assignment', distinct=True),
            submission_count=Count('submissions'),
            avg_score=Avg('submissions__score'),
            completed_assignments=Count(
                'submissions',
                filter=Q(submissions__score__isnull=False)
            )
        ).values(
            'id', 'username', 'email', 'assignment_count',
            'submission_count', 'avg_score', 'completed_assignments'
        ).order_by('-avg_score')

    def _get_avg_classroom_performance(self):
        """Helper method to calculate average classroom performance."""
        result = Classroom.objects.filter(school=self.school).aggregate(
            avg_performance=Avg(
                Submission.objects.filter(
                    assignment__classroom__school=self.school,
                    score__isnull=False
                ).values('score')
            )
        )
        return result['avg_performance']


class ManagementAnalyticsService(BaseAnalyticsService):
    """Analytics service for Management dashboard."""

    def __init__(self, user):
        self.user = user
        self.school = user.school

    def get_course_completion_rates(self):
        """Get course completion rates for managed classrooms."""
        teacher_emails = self.user.sent_invites.filter(
            role='teacher', accepted=True
        ).values_list('email', flat=True)
        teachers = User.objects.filter(
            email__in=teacher_emails, role='teacher'
        )

        return Classroom.objects.filter(
            school=self.school, teacher__in=teachers
        ).annotate(
            total_assignments=Count('assignments'),
            completed_submissions=Count(
                'assignments__submissions',
                filter=Q(assignments__submissions__score__isnull=False)
            ),
            total_expected=Count('assignments') * Count('students'),
            completion_rate=Case(
                When(total_expected=0, then=0),
                default=Count('assignments__submissions', filter=Q(assignments__submissions__score__isnull=False)) * 100.0 / (Count('assignments') * Count('students')),
                output_field=IntegerField()
            )
        ).values(
            'id', 'name', 'total_assignments', 'completed_submissions',
            'total_expected', 'completion_rate'
        )

    def get_assignment_submission_analytics(self):
        """Get assignment submission analytics."""
        teacher_emails = self.user.sent_invites.filter(
            role='teacher', accepted=True
        ).values_list('email', flat=True)
        teachers = User.objects.filter(
            email__in=teacher_emails, role='teacher'
        )

        return Assignment.objects.filter(
            classroom__school=self.school,
            classroom__teacher__in=teachers
        ).annotate(
            total_students=Count('classroom__students'),
            submissions_count=Count('submissions'),
            late_submissions=Count('submissions', filter=Q(submissions__submitted_at__gt=F('due_date'))),
            submission_rate=Case(
                When(classroom__students__isnull=True, then=0),
                default=Count('submissions') * 100.0 / Count('classroom__students'),
                output_field=IntegerField()
            )
        ).values(
            'id', 'title', 'due_date', 'total_students',
            'submissions_count', 'late_submissions', 'submission_rate'
        )

    def get_engagement_metrics(self):
        """Get engagement metrics for managed area."""
        last_30_days = timezone.now() - timedelta(days=30)
        teacher_emails = self.user.sent_invites.filter(
            role='teacher', accepted=True
        ).values_list('email', flat=True)
        teachers = User.objects.filter(
            email__in=teacher_emails, role='teacher'
        )

        return {
            'active_students': User.objects.filter(
                role='student',
                school=self.school,
                last_login__gte=last_30_days
            ).count(),
            'messages_sent': Message.objects.filter(
                sender__school=self.school,
                sender__in=teachers,
                created_at__gte=last_30_days
            ).count(),
            'announcements_created': Announcement.objects.filter(
                classroom__school=self.school,
                classroom__teacher__in=teachers,
                created_at__gte=last_30_days
            ).count(),
        }

    def get_department_performance(self):
        """Get performance by department/classroom."""
        teacher_emails = self.user.sent_invites.filter(
            role='teacher', accepted=True
        ).values_list('email', flat=True)
        teachers = User.objects.filter(
            email__in=teacher_emails, role='teacher'
        )

        return Classroom.objects.filter(
            school=self.school, teacher__in=teachers
        ).annotate(
            avg_score=Avg('assignments__submissions__score'),
            submission_rate=Count('assignments__submissions') * 100.0 / (Count('assignments') * Count('students')),
            student_count=Count('students')
        ).values(
            'id', 'name', 'avg_score', 'submission_rate', 'student_count'
        ).order_by('-avg_score')


class TeacherAnalyticsService(BaseAnalyticsService):
    """Analytics service for Teacher dashboard."""

    def __init__(self, user, classroom_id=None):
        self.user = user
        self.classroom_id = classroom_id

    def get_class_performance(self):
        """Get performance metrics for teacher's classrooms."""
        return Classroom.objects.filter(teacher=self.user).annotate(
            total_students_count=Count('students'),
            assignment_count=Count('assignments'),
            avg_score=Avg('assignments__submissions__score'),
            submission_rate=Case(
                When(students__isnull=True, then=0),
                default=Count('assignments__submissions') * 100.0 / (Count('assignments') * Count('students')),
                output_field=IntegerField()
            )
        ).values(
            'id', 'name', 'code', 'total_students_count', 'assignment_count',
            'avg_score', 'submission_rate'
        )

    def get_student_wise_performance(self, classroom_id=None):
        """Get performance data for each student."""
        queryset = User.objects.filter(
            joined_classrooms__teacher=self.user
        )
        if classroom_id:
            queryset = queryset.filter(joined_classrooms__id=classroom_id)
            
        return queryset.distinct().annotate(
            classroom_count=Count('joined_classrooms', distinct=True),
            assignment_count=Count('submissions__assignment', distinct=True, filter=Q(submissions__assignment__classroom_id=classroom_id) if classroom_id else Q()),
            submission_count=Count('submissions', filter=Q(submissions__assignment__classroom_id=classroom_id) if classroom_id else Q()),
            avg_score=Avg('submissions__score', filter=Q(submissions__assignment__classroom_id=classroom_id) if classroom_id else Q()),
            completed_count=Count('submissions', filter=Q(submissions__score__isnull=False, submissions__assignment__classroom_id=classroom_id) if classroom_id else Q())
        ).values(
            'id', 'username', 'email', 'classroom_count', 'assignment_count',
            'submission_count', 'avg_score', 'completed_count'
        ).order_by('-avg_score')

    def get_assignment_analytics(self, classroom_id=None):
        """Get detailed assignment analytics."""
        queryset = Assignment.objects.filter(
            classroom__teacher=self.user
        )
        if classroom_id:
            queryset = queryset.filter(classroom_id=classroom_id)
            
        return queryset.annotate(
            total_students=Count('classroom__students'),
            submissions_count=Count('submissions'),
            late_submissions=Count('submissions', filter=Q(submissions__submitted_at__gt=F('due_date'))),
            avg_score=Avg('submissions__score'),
            submission_rate=Case(
                When(classroom__students__isnull=True, then=0),
                default=Count('submissions') * 100.0 / Count('classroom__students'),
                output_field=IntegerField()
            )
        ).values(
            'id', 'title', 'classroom__name', 'due_date', 'total_students', 'submissions_count',
            'late_submissions', 'avg_score', 'submission_rate'
        )

    def identify_weak_students(self):
        """Identify students who need attention."""
        queryset = User.objects.filter(
            joined_classrooms__teacher=self.user
        )
        if self.classroom_id:
            queryset = queryset.filter(joined_classrooms__id=self.classroom_id)
            
        return queryset.distinct().annotate(
            avg_score=Avg('submissions__score', filter=Q(submissions__assignment__classroom_id=self.classroom_id) if self.classroom_id else Q()),
            submission_count=Count('submissions', filter=Q(submissions__assignment__classroom_id=self.classroom_id) if self.classroom_id else Q()),
            late_count=Count('submissions', filter=Q(
                submissions__submitted_at__gt=F('submissions__assignment__due_date'),
                submissions__assignment__classroom_id=self.classroom_id if self.classroom_id else Q()
            ))
        ).filter(
            Q(avg_score__lt=60) | Q(submission_count=0)
        ).values(
            'id', 'username', 'email', 'avg_score', 'submission_count', 'late_count'
        ).order_by('avg_score')

    def get_classroom_performance_metrics(self, classroom_id):
        """Get detailed metrics for a specific classroom."""
        classroom = Classroom.objects.filter(teacher=self.user, id=classroom_id).annotate(
            total_students_count=Count('students', distinct=True),
            assignment_count=Count('assignments', distinct=True),
            submission_count=Count('assignments__submissions'),
            avg_score=Avg('assignments__submissions__score'),
            submission_rate=Case(
                When(students__isnull=True, then=0),
                default=Count('assignments__submissions') * 100.0 / (Count('assignments') * Count('students')),
                output_field=IntegerField()
            )
        ).first()
        
        if not classroom:
            return None
            
        return {
            'classroom': classroom,
            'students_performance': self.get_student_wise_performance(classroom_id),
            'assignments_analytics': self.get_assignment_analytics(classroom_id),
            'weak_students': self.identify_weak_students_for_classroom(classroom_id),
        }

    def identify_weak_students_for_classroom(self, classroom_id):
        """Identify weak students in a specific classroom."""
        return User.objects.filter(
            joined_classrooms__id=classroom_id,
            joined_classrooms__teacher=self.user
        ).distinct().annotate(
            avg_score=Avg('submissions__score', filter=Q(submissions__assignment__classroom_id=classroom_id)),
            submission_count=Count('submissions', filter=Q(submissions__assignment__classroom_id=classroom_id)),
            late_count=Count('submissions', filter=Q(
                submissions__submitted_at__gt=F('submissions__assignment__due_date'),
                submissions__assignment__classroom_id=classroom_id
            ))
        ).filter(
            Q(avg_score__lt=60) | Q(submission_count=0)
        ).values(
            'id', 'username', 'email', 'avg_score', 'submission_count', 'late_count'
        ).order_by('avg_score')


class StudentAnalyticsService(BaseAnalyticsService):
    """Analytics service for Student dashboard."""

    def __init__(self, user):
        self.user = user

    def get_personal_performance_dashboard(self):
        """Get student's overall performance metrics."""
        from django.db.models import Sum
        submissions = self.user.submissions.filter(score__isnull=False).select_related('assignment')
        total_score = sum(s.score for s in submissions)
        total_max   = sum(s.assignment.max_score for s in submissions)
        avg_pct     = round(total_score / total_max * 100, 1) if total_max else None
        return {
            'total_assignments': Assignment.objects.filter(
                classroom__students=self.user
            ).count(),
            'submitted_assignments': self.user.submissions.count(),
            'graded_assignments': submissions.count(),
            'avg_score': avg_pct,
            'classroom_count': self.user.joined_classrooms.count(),
        }

    def get_progress_trends(self):
        """Get student's progress over time as percentage scores."""
        from django.db.models.functions import TruncMonth
        submissions = self.user.submissions.filter(
            score__isnull=False
        ).select_related('assignment').order_by('submitted_at')

        # Group by month manually to compute percentage correctly
        from collections import defaultdict
        monthly = defaultdict(lambda: {'scores': [], 'maxes': []})
        for s in submissions:
            key = s.submitted_at.strftime('%Y-%m-01')
            monthly[key]['scores'].append(s.score)
            monthly[key]['maxes'].append(s.assignment.max_score)

        result = []
        for month_str in sorted(monthly.keys()):
            data = monthly[month_str]
            total_score = sum(data['scores'])
            total_max   = sum(data['maxes'])
            pct = round(total_score / total_max * 100, 1) if total_max else 0
            from django.utils.dateparse import parse_datetime
            import datetime
            month_dt = datetime.datetime.strptime(month_str, '%Y-%m-%d')
            result.append({
                'month':     month_dt,
                'avg_score': pct,
                'count':     len(data['scores']),
            })
        return result

    def get_assignment_tracking(self, month=None):
        """Get assignment completion status for this student only."""
        from django.db.models import OuterRef, Subquery, BooleanField, DateTimeField
        from assignments.models import Submission

        assignments = Assignment.objects.filter(
            classroom__students=self.user
        )

        if month:
            try:
                year, month_value = map(int, month.split('-'))
                assignments = assignments.filter(
                    due_date__year=year, due_date__month=month_value
                )
            except ValueError:
                pass

        # Subqueries scoped to this student only
        my_sub = Submission.objects.filter(
            assignment=OuterRef('pk'), student=self.user
        )

        assignments = assignments.annotate(
            submitted=Case(
                When(pk__in=Submission.objects.filter(student=self.user).values('assignment_id'), then=True),
                default=False,
                output_field=IntegerField()
            ),
            score=Subquery(my_sub.values('score')[:1]),
            submitted_at=Subquery(my_sub.values('submitted_at')[:1]),
            is_late=Case(
                When(
                    pk__in=Submission.objects.filter(
                        student=self.user,
                        submitted_at__gt=F('assignment__due_date')
                    ).values('assignment_id'),
                    then=True
                ),
                default=False,
                output_field=IntegerField()
            )
        ).values(
            'id', 'title', 'due_date', 'max_score', 'submitted',
            'score', 'submitted_at', 'is_late'
        ).order_by('-due_date').distinct()

        return assignments

    def get_strengths_and_weaknesses(self):
        """Analyze student's performance as percentages."""
        submissions = self.user.submissions.filter(
            score__isnull=False
        ).select_related('assignment')

        if not submissions.exists():
            return {
                'graded_assignments': 0,
                'avg_score': None,
                'highest_score': None,
                'lowest_score': None,
            }

        pcts = [
            round(s.score / s.assignment.max_score * 100, 1)
            for s in submissions
            if s.assignment.max_score > 0
        ]
        return {
            'graded_assignments': submissions.count(),
            'avg_score':     round(sum(pcts) / len(pcts), 1) if pcts else None,
            'highest_score': max(pcts) if pcts else None,
            'lowest_score':  min(pcts) if pcts else None,
        }

    def get_class_rank(self):
        """Get student's rank in each classroom."""
        ranks = []
        for classroom in self.user.joined_classrooms.all():
            # Calculate rank based on average score
            student_scores = User.objects.filter(
                joined_classrooms=classroom
            ).annotate(
                avg_score=Avg('submissions__score')
            ).filter(
                avg_score__isnull=False
            ).values('id', 'username', 'avg_score').order_by('-avg_score')

            student_list = list(student_scores)
            student_rank = None
            for i, student in enumerate(student_list, 1):
                if student['id'] == self.user.id:
                    student_rank = i
                    break

            ranks.append({
                'classroom': classroom,
                'rank': student_rank,
                'total_students': len(student_list),
                'avg_score': self.user.submissions.filter(
                    assignment__classroom=classroom,
                    score__isnull=False
                ).aggregate(avg=Avg('score'))['avg']
            })

        return ranks