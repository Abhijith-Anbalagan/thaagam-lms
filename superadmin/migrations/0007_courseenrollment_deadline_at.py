from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


def populate_deadlines(apps, schema_editor):
    CourseEnrollment = apps.get_model('superadmin', 'CourseEnrollment')
    for enrollment in CourseEnrollment.objects.filter(deadline_at__isnull=True):
        enrolled_at = enrollment.enrolled_at or timezone.now()
        enrollment.deadline_at = enrolled_at + timedelta(days=30)
        enrollment.save(update_fields=['deadline_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('superadmin', '0006_classroomcourseassignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseenrollment',
            name='deadline_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(populate_deadlines, migrations.RunPython.noop),
    ]
