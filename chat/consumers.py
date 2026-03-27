import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from chat.models import Message
from classrooms.models import Classroom


def _room(classroom_id, user_a, user_b):
    """Shared room name for a pair — order-independent."""
    lo, hi = sorted([int(user_a), int(user_b)])
    return f'chat_{classroom_id}_{lo}_{hi}'


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.classroom_id = self.scope['url_route']['kwargs']['classroom_id']
        user = self.scope['user']
        if not user.is_authenticated or user.role not in ('student', 'teacher'):
            await self.close()
            return
        if not await self.user_in_classroom(user, self.classroom_id):
            await self.close()
            return
        # Each user joins their own personal room so the receiver_id sent
        # from the client determines which shared pair-room to use.
        self.user = user
        self.personal_room = f'user_{user.pk}'
        await self.channel_layer.group_add(self.personal_room, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'personal_room'):
            await self.channel_layer.group_discard(self.personal_room, self.channel_name)

    async def receive(self, text_data):
        data        = json.loads(text_data)
        body        = data.get('body', '').strip()
        receiver_id = data.get('receiver_id')
        if not body or not receiver_id:
            return
        user    = self.user
        message = await self.save_message(user.pk, int(receiver_id), int(self.classroom_id), body)
        payload = {
            'type':        'chat_message',
            'sender_id':   user.pk,
            'sender_name': user.get_full_name() or user.username,
            'body':        body,
            'created_at':  message.created_at.strftime('%H:%M'),
        }
        # Deliver to sender's personal room (echo back) and receiver's personal room
        for room in [f'user_{user.pk}', f'user_{receiver_id}']:
            await self.channel_layer.group_send(room, payload)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def user_in_classroom(self, user, classroom_id):
        try:
            classroom = Classroom.objects.get(pk=classroom_id)
        except Classroom.DoesNotExist:
            return False
        if user.role == 'teacher':
            return classroom.teacher_id == user.pk
        return classroom.students.filter(pk=user.pk).exists()

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, classroom_id, body):
        return Message.objects.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            classroom_id=classroom_id,
            body=body,
        )
