from django.db import models


class Message(models.Model):
    classroom  = models.ForeignKey('classrooms.Classroom', on_delete=models.CASCADE, related_name='messages')
    sender     = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='sent_messages')
    receiver   = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='received_messages')
    body       = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} → {self.receiver}: {self.body[:40]}'

    @property
    def has_attachment(self):
        return bool(self.attachment)
