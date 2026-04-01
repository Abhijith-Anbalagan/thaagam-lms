from django.urls import path
from chat import views

urlpatterns = [
    path('upload/<int:classroom_id>/', views.upload_attachment, name='chat_upload_attachment'),
]
