import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.classroom_id = self.scope['url_route']['kwargs']['classroom_id']
        user = self.scope['user']
        if not user.is_authenticated or user.role not in ('student', 'teacher'):
            await self.close()
            return
        # Each user gets their own personal group so messages are routed correctly
        self.room = f'chat_{self.classroom_id}_{user.pk}'
        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'room'):
            await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive(self, text_data):
        data        = json.loads(text_data)
        body        = data.get('body', '').strip()
        receiver_id = data.get('receiver_id')
        if not body or not receiver_id:
            return
        user    = self.scope['user']
        message = await self.save_message(
            user.pk, int(receiver_id), int(self.classroom_id), body
        )
        payload = {
            'type':        'chat_message',
            'sender_id':   user.pk,
            'sender_name': user.get_full_name() or user.username,
            'body':        body,
            'created_at':  message.created_at.strftime('%H:%M'),
        }
        # Send to both sender's and receiver's personal groups
        for grp in [
            f'chat_{self.classroom_id}_{user.pk}',
            f'chat_{self.classroom_id}_{receiver_id}',
        ]:
            await self.channel_layer.group_send(grp, payload)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, classroom_id, body):
        from chat.models import Message
        return Message.objects.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            classroom_id=classroom_id,
            body=body,
        )
