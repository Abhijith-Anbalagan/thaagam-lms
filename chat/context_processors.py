from .models import Message
from django.db.models import Q

def unread_messages_count(request):
    if request.user.is_authenticated:
        # For simplicity, count all unread messages where the user is the receiver
        count = Message.objects.filter(receiver=request.user, is_read=False).count()
        return {'unread_messages_count': count}
    return {'unread_messages_count': 0}
