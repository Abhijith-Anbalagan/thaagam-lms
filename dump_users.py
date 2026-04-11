from accounts.models import User
print("USER DUMP:")
for u in User.objects.all():
    print(f"Email: {u.email} | Avatar: '{u.avatar.name if u.avatar else 'None'}'")
