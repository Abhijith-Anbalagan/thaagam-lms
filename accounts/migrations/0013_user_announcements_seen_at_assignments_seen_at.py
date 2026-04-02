from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_merge_20260402_1257'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='announcements_seen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='assignments_seen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
