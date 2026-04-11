from accounts.models import User
import os

print("Starting avatar repair...")
for u in User.objects.all():
    if u.avatar:
        old_name = u.avatar.name
        changed = False
        new_name = old_name
        
        # 1. Replace spaces with underscores
        if ' ' in new_name:
            new_name = new_name.replace(' ', '_')
            changed = True
            
        # 2. Add 'avatars/' prefix if missing
        if not new_name.startswith('avatars/'):
            new_name = 'avatars/' + new_name
            changed = True
            
        if changed:
            u.avatar.name = new_name
            u.save()
            print(f"Fixed {u.email}: {old_name} -> {new_name}")
print("Finished.")
