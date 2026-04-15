import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from classrooms.models import Classroom
from chat.models import Message
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from zoneinfo import ZoneInfo

CHAT_TIMEZONE = ZoneInfo('Asia/Kolkata')

ALLOWED_MIME_PREFIXES = ('image/', 'application/pdf', 'application/msword',
    'application/vnd.openxmlformats', 'application/vnd.ms-',
    'text/plain', 'application/zip',
)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@login_required
@require_POST
def upload_attachment(request, classroom_id):
    user = request.user
    classroom = get_object_or_404(Classroom, pk=classroom_id)

    # Verify membership
    if user.role == 'teacher':
        if classroom.teacher_id != user.pk:
            return JsonResponse({'error': 'Forbidden'}, status=403)
    else:
        if not classroom.students.filter(pk=user.pk).exists():
            return JsonResponse({'error': 'Forbidden'}, status=403)

    receiver_id = request.POST.get('receiver_id')
    if not receiver_id:
        return JsonResponse({'error': 'receiver_id required'}, status=400)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file'}, status=400)

    if file.size > MAX_UPLOAD_BYTES:
        return JsonResponse({'error': 'File too large (max 10 MB)'}, status=400)

    content_type = getattr(file, 'content_type', '') or ''
    if not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        return JsonResponse({'error': 'File type not allowed'}, status=400)

    body = request.POST.get('body', '').strip()

    msg = Message.objects.create(
        classroom=classroom,
        sender=user,
        receiver_id=int(receiver_id),
        body=body,
        attachment=file,
    )
    msg.refresh_from_db()

    is_image = content_type.startswith('image/')
    payload = {
        'type':          'chat_message',
        'sender_id':     user.pk,
        'sender_name':   user.get_full_name() or user.username,
        'body':          body,
        'created_at':    msg.created_at.astimezone(CHAT_TIMEZONE).strftime('%I:%M %p'),
        'attachment_url': msg.attachment.url,
        'attachment_name': os.path.basename(msg.attachment.name),
        'is_image':      is_image,
    }

    channel_layer = get_channel_layer()
    if channel_layer:
        # Notify receiver
        async_to_sync(channel_layer.group_send)(
            f'notifications_{msg.receiver_id}',
            {
                'type': 'notification',
                'payload': {
                    'type': 'chat',
                    'classroom_id': classroom_id,
                    'redirect_url': f'{"/student" if msg.receiver.role == "student" else "/teacher"}/classroom/{classroom_id}/chat/',
                    'sender_name': payload['sender_name'],
                    'body': '📎 Attached a file' + (f': {body}' if body else ''),
                },
            },
        )
        for room in [f'user_{user.pk}', f'user_{receiver_id}']:
            async_to_sync(channel_layer.group_send)(room, payload)

    return JsonResponse({'ok': True, 'message_id': msg.pk})
