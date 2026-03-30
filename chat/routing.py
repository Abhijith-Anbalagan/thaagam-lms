from django.urls import re_path
from . import consumers
websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<classroom_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/status/(?P<classroom_id>\d+)/$', consumers.UserStatusConsumer.as_asgi()),
    re_path(r'ws/presence/$', consumers.PresenceConsumer.as_asgi()),
    re_path(r'ws/student-notifications/$', consumers.StudentNotificationConsumer.as_asgi()),
]
