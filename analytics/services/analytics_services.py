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
            student_count=Count('students'),
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

    def __init__(self, user):
        self.user = user

    def get_class_performance(self):
        """Get performance metrics for teacher's classrooms."""
        return Classroom.objects.filter(teacher=self.user).annotate(
            student_count=Count('students'),
            assignment_count=Count('assignments'),
            avg_score=Avg('assignments__submissions__score'),
            submission_rate=Case(
                When(students__isnull=True, then=0),
                default=Count('assignments__submissions') * 100.0 / (Count('assignments') * Count('students')),
                output_field=IntegerField()
            )
        ).values(
            'id', 'name', 'student_count', 'assignment_count',
            'avg_score', 'submission_rate'
        )

    def get_student_wise_performance(self):
        """Get performance data for each student."""
        return User.objects.filter(
            joined_classrooms__teacher=self.user
        ).distinct().annotate(
            classroom_count=Count('joined_classrooms', distinct=True),
            assignment_count=Count('submissions__assignment', distinct=True),
            submission_count=Count('submissions'),
            avg_score=Avg('submissions__score'),
            completed_count=Count('submissions', filter=Q(submissions__score__isnull=False))
        ).values(
            'id', 'username', 'email', 'classroom_count', 'assignment_count',
            'submission_count', 'avg_score', 'completed_count'
        ).order_by('-avg_score')

    def get_assignment_analytics(self):
        """Get detailed assignment analytics."""
        return Assignment.objects.filter(
            classroom__teacher=self.user
        ).annotate(
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
            'id', 'title', 'due_date', 'total_students', 'submissions_count',
            'late_submissions', 'avg_score', 'submission_rate'
        )

    def identify_weak_students(self):
        """Identify students who need attention."""
        return User.objects.filter(
            joined_classrooms__teacher=self.user
        ).distinct().annotate(
            avg_score=Avg('submissions__score'),
            submission_count=Count('submissions'),
            late_count=Count('submissions', filter=Q(submissions__submitted_at__gt=F('submissions__assignment__due_date')))
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
        return {
            'total_assignments': Assignment.objects.filter(
                classroom__students=self.user
            ).count(),
            'submitted_assignments': self.user.submissions.count(),
            'graded_assignments': self.user.submissions.filter(
                score__isnull=False
            ).count(),
            'avg_score': self.user.submissions.aggregate(
                avg=Avg('score')
            )['avg'],
            'classroom_count': self.user.joined_classrooms.count(),
        }

    def get_progress_trends(self):
        """Get student's progress over time."""
        return self.user.submissions.filter(
            score__isnull=False
        ).annotate(
            month=TruncMonth('submitted_at')
        ).values('month').annotate(
            avg_score=Avg('score'),
            count=Count('id')
        ).order_by('month')

    def get_assignment_tracking(self, month=None):
        """Get assignment completion status, optionally filtered by month."""
        assignments = Assignment.objects.filter(
            classroom__students=self.user
        )

        if month:
            try:
                year, month_value = map(int, month.split('-'))
                assignments = assignments.filter(due_date__year=year, due_date__month=month_value)
            except ValueError:
                pass

        assignments = assignments.annotate(
            submitted=Case(
                When(submissions__student=self.user, then=True),
                default=False,
                output_field=IntegerField()
            ),
            score=F('submissions__score'),
            submitted_at=F('submissions__submitted_at'),
            is_late=Case(
                When(submissions__student=self.user, submissions__submitted_at__gt=F('due_date'), then=True),
                default=False,
                output_field=IntegerField()
            )
        ).values(
            'id', 'title', 'due_date', 'max_score', 'submitted',
            'score', 'submitted_at', 'is_late'
        ).order_by('-due_date')

        return assignments

    def get_strengths_and_weaknesses(self):
        """Analyze student's performance patterns."""
        # Group by assignment type or score ranges
        submissions = self.user.submissions.filter(score__isnull=False)

        return {
            'graded_assignments': submissions.count(),
            'avg_score': submissions.aggregate(avg=Avg('score'))['avg'],
            'highest_score': submissions.aggregate(max=Max('score'))['max'],
            'lowest_score': submissions.aggregate(min=Min('score'))['min'],
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