from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notify_user(user_id, payload):
    channel_layer = get_channel_layer()
    if not channel_layer: return
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {'type': 'notification', 'payload': payload}
    )

def notify_users(user_ids, payload):
    channel_layer = get_channel_layer()
    if not channel_layer: return
    for uid in set(user_ids):
        async_to_sync(channel_layer.group_send)(
            f'notifications_{uid}',
            {'type': 'notification', 'payload': payload}
        )
