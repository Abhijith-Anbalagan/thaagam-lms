from accounts.models import User, StudentCredentialLog
print(f'Student Count: {User.objects.filter(role="student").count()}')
print(f'Log Count: {StudentCredentialLog.objects.count()}')
for log in StudentCredentialLog.objects.all():
    print(f'Log: {log.student_name} | {log.generated_id} | {log.plain_password}')
