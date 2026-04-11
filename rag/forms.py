from django import forms
from .models import RAGDocument

class RAGDocumentForm(forms.ModelForm):
    class Meta:
        model = RAGDocument
        fields = ['title', 'file']
