

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('classrooms', '0003_classroom_is_active'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='classroom',
            name='is_active',
        ),
    ]
