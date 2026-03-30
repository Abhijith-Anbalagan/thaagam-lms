import json
from zoneinfo import ZoneInfo
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from chat.models import Message
from classrooms.models import Classroom

CHAT_TIMEZONE = ZoneInfo('Asia/Kolkata')


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
        
        # Broadcast user online status
        await self.channel_layer.group_send(
            f'user_status_{self.classroom_id}',
            {
                'type': 'user_status_update',
                'user_id': user.pk,
                'user_name': user.get_full_name() or user.username,
                'status': 'online',
                'role': user.role,
            }
        )

    async def disconnect(self, code):
        if hasattr(self, 'personal_room'):
            await self.channel_layer.group_discard(self.personal_room, self.channel_name)
        
        # Broadcast user offline status
        if hasattr(self, 'user') and hasattr(self, 'classroom_id'):
            await self.channel_layer.group_send(
                f'user_status_{self.classroom_id}',
                {
                    'type': 'user_status_update',
                    'user_id': self.user.pk,
                    'user_name': self.user.get_full_name() or self.user.username,
                    'status': 'offline',
                    'role': self.user.role,
                }
            )

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
            'created_at':  message.created_at.astimezone(CHAT_TIMEZONE).strftime('%I:%M %p'),
        }

        if message.receiver.role == 'student':
            await self.channel_layer.group_send(
                f'student_notifications_{message.receiver_id}',
                {
                    'type': 'student_notification',
                    'payload': {
                        'type': 'chat',
                        'classroom_id': int(self.classroom_id),
                        'redirect_url': f'/student/classroom/{self.classroom_id}/chat/',
                        'sender_name': payload['sender_name'],
                    },
                },
            )

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
        message = Message.objects.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            classroom_id=classroom_id,
            body=body,
        )
        return Message.objects.select_related('receiver').get(pk=message.pk)


class UserStatusConsumer(AsyncWebsocketConsumer):
    """Handle real-time user status updates (online/offline)."""

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        
        # Get classroom ID from URL
        try:
            classroom_id = self.scope['url_route']['kwargs'].get('classroom_id')
            if not classroom_id:
                await self.close()
                return
            
            # Verify user is in the classroom
            if not await self.user_in_classroom(user, classroom_id):
                await self.close()
                return
                
        except:
            await self.close()
            return

        self.classroom_id = classroom_id
        self.user = user
        self.group_name = f'user_status_{classroom_id}'
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Send initial online status
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_status_update',
                'user_id': user.pk,
                'user_name': user.get_full_name() or user.username,
                'status': 'online',
                'role': user.role,
            }
        )

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            # Broadcast offline status
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_status_update',
                    'user_id': self.user.pk,
                    'user_name': self.user.get_full_name() or self.user.username,
                    'status': 'offline',
                    'role': self.user.role,
                }
            )
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def user_status_update(self, event):
        """Handle status update messages."""
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'status': event['status'],
            'role': event['role'],
        }))

    @database_sync_to_async
    def user_in_classroom(self, user, classroom_id):
        try:
            classroom = Classroom.objects.get(pk=classroom_id)
        except Classroom.DoesNotExist:
            return False
        if user.role == 'teacher':
            return classroom.teacher_id == user.pk
        return classroom.students.filter(pk=user.pk).exists()


class PresenceConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return

        self.group_name = 'presence'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send full teacher online snapshot on connect.
        online_teacher_ids = await self.get_online_teachers()
        await self.send(text_data=json.dumps({
            'type': 'presence.snapshot',
            'online_teachers': online_teacher_ids,
        }))

    @database_sync_to_async
    def get_online_teachers(self):
        from django.core.cache import cache
        from accounts.models import User

        online_teacher_ids = []
        for t in User.objects.filter(role='teacher'):
            # Check if cache value is explicitly True (not None or False)
            if cache.get(f'user_online_{t.pk}') is True:
                online_teacher_ids.append(t.pk)
        return online_teacher_ids

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def presence_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence.update',
            'user_id': event['user_id'],
            'user_role': event['user_role'],
            'status': event['status'],
        }))


class StudentNotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated or user.role != 'student':
            await self.close()
            return

        self.group_name = f'student_notifications_{user.pk}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def student_notification(self, event):
        await self.send(text_data=json.dumps(event['payload']))
