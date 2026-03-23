from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Create a super_admin user for EduPlatform'
    def add_arguments(self, parser):
        parser.add_argument('--username', default='superadmin')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--email',    default='admin@eduplatform.com')
    def handle(self, *args, **options):
        u, pw = options['username'], options['password']
        if User.objects.filter(username=u).exists():
            self.stdout.write(self.style.WARNING(f'User "{u}" already exists.')); return
        user = User.objects.create(username=u, email=options['email'],
                                   first_name='Super', last_name='Admin',
                                   role='super_admin', is_staff=True, is_superuser=True)
        user.set_password(pw); user.save()
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Super Admin created!\n   Username : {u}\n   Password : {pw}\n   URL      : /login/\n'))
