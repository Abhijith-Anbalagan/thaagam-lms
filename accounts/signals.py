"""
Signals for the accounts app.
Tracks login/logout status for teacher presence real-time features.
"""
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.cache import cache
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@receiver(user_logged_in)
def user_logged_in_handler(sender, user, request, **kwargs):
    cache.set(f'user_online_{user.pk}', True, timeout=None)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'presence',
        {
            'type': 'presence.update',
            'user_id': user.pk,
            'user_role': user.role,
            'status': 'online',
        }
    )


@receiver(user_logged_out)
def user_logged_out_handler(sender, user, request, **kwargs):
    from django.utils import timezone as tz
    from accounts.models import User
    now = tz.now()
    cache.set(f'user_online_{user.pk}', False, timeout=None)
    # Save last_seen on logout
    User.objects.filter(pk=user.pk).update(last_seen=now)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'presence',
        {
            'type': 'presence.update',
            'user_id': user.pk,
            'user_role': user.role,
            'status': 'offline',
            'last_seen': now.isoformat(),
        }
    )
