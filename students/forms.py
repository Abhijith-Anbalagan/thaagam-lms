from django import forms
from assignments.models import Submission


class JoinClassroomForm(forms.Form):
    class_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control mono',
            'placeholder': 'ABC123',
            'style': 'text-transform:uppercase;letter-spacing:4px;font-size:18px;',
            'maxlength': '6',
            'autofocus': True
        })
    )

    def clean_class_code(self):
        code = self.cleaned_data.get('class_code', '').upper().strip()
        if len(code) != 6:
            raise forms.ValidationError('Class code must be exactly 6 characters.')
        return code


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }
