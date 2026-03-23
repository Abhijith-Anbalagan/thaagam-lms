"""
Signals for the accounts app.
Currently empty — add post_save signals here as needed.
Example: auto-send welcome email after user creation.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
# from .models import User

# @receiver(post_save, sender=User)
# def user_created(sender, instance, created, **kwargs):
#     if created:
#         pass  # send welcome email, etc.
