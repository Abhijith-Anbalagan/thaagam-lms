from django import forms
from .models import Assignment, Submission


class AssignmentForm(forms.ModelForm):
    class Meta:
        model   = Assignment
        fields  = ['title', 'description', 'due_date', 'max_score', 'file']
        widgets = {
            'due_date':    forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make datetime-local format work with Django
        if self.instance and self.instance.due_date:
            self.initial['due_date'] = self.instance.due_date.strftime('%Y-%m-%dT%H:%M')


class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model  = Submission
        fields = ['score', 'feedback']
        widgets = {
            'feedback': forms.TextInput(attrs={'placeholder': 'Optional feedback for student…'}),
        }

    def __init__(self, *args, max_score=20, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['score'].widget = forms.NumberInput(attrs={
            'min': 0, 'max': max_score, 'placeholder': f'0–{max_score}',
            'style': 'width:72px;',
        })
        self.fields['score'].required = False
