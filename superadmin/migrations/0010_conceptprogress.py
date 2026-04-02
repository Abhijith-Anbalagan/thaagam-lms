from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('superadmin', '0009_alter_school_deadline_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ConceptProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('concept', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress_records', to='superadmin.globalconcept')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='concept_progress', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'superadmin_conceptprogress',
                'unique_together': {('student', 'concept')},
            },
        ),
    ]
