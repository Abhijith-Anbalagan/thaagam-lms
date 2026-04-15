from django.urls import path
from . import views

urlpatterns = [
    # Admin views
    path('manage/', views.manage_documents, name='rag_manage_documents'),
    path('upload/', views.upload_document, name='rag_upload_document'),
    path('sync/<int:doc_id>/', views.sync_document, name='rag_sync_document'),
    path('delete/<int:doc_id>/', views.delete_document, name='rag_delete_document'),
    
    # Student views
    path('chat/', views.student_chat, name='rag_student_chat'),
    path('api/chat/', views.api_chat_proxy, name='rag_api_chat_proxy'),
]
