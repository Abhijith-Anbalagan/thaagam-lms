from django import forms
from accounts.models import User
from .models import School, GlobalCourse, GlobalConcept, GlobalConceptVideo


class SchoolForm(forms.ModelForm):
    class Meta:
        model  = School
        fields = ['name', 'address']


class SchoolEditForm(forms.ModelForm):
    class Meta:
        model  = School
        fields = ['name', 'address']


class AdminEditForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email']


class GlobalCourseForm(forms.ModelForm):
    schools = forms.ModelMultipleChoiceField(
        queryset=School.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Assign to Schools',
    )

    class Meta:
        model  = GlobalCourse
        fields = ['title', 'description', 'cover_image', 'language',
                  'total_hours', 'is_free', 'has_certificate', 'summary', 'schools']
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 4}),
        }


class GlobalConceptForm(forms.ModelForm):
    """
    Form for the 5-step wizard concept creation.
    Step 1: header, h3_course
    Step 2: level (handled in template), videos (handled separately)
    Step 3: pdf
    Step 4: quiz
    Step 5: assignment
    """
    class Meta:
        model  = GlobalConcept
        fields = ['header', 'h3_course', 'level', 'pdf', 'quiz', 'assignment']
        widgets = {
            'header': forms.TextInput(attrs={
                'class': 'fc',
                'placeholder': 'e.g., Introduction to Variables'
            }),
            'h3_course': forms.TextInput(attrs={
                'class': 'fc',
                'placeholder': 'e.g., Programming Fundamentals'
            }),
            'quiz': forms.Textarea(attrs={
                'rows': 4,
                'style': 'display:none'  # Hidden - managed by JavaScript
            }),
            'assignment': forms.Textarea(attrs={
                'rows': 4,
                'style': 'display:none'  # Hidden - managed by JavaScript
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make level not required in form since it's handled by template
        self.fields['level'].required = False
        self.fields['pdf'].required = False
        self.fields['quiz'].required = False
        self.fields['assignment'].required = False