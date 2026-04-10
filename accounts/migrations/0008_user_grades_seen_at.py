from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_user_last_seen'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='grades_seen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
