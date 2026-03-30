from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notify_students(student_ids, payload):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    for student_id in set(student_ids):
        async_to_sync(channel_layer.group_send)(
            f'student_notifications_{student_id}',
            {
                'type': 'student_notification',
                'payload': payload,
            },
        )
