from django.db import models
from django.conf import settings

class RAGDocument(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='rag_documents/')
    school = models.ForeignKey('superadmin.School', on_delete=models.CASCADE, null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    external_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID returned by the external RAG API")
    status = models.CharField(max_length=50, default='pending', help_text="Status of processing in the external API")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    query = models.TextField()
    response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat by {self.user.username} at {self.timestamp}"
