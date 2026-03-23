from django import forms
from .models import Assignment, Submission

class AssignmentForm(forms.ModelForm):
    class Meta:
        model  = Assignment
        fields = ['title', 'description', 'due_date', 'max_score', 'file']
        widgets = {'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'})}

class SubmissionForm(forms.ModelForm):
    class Meta:
        model  = Submission
        fields = ['file']
