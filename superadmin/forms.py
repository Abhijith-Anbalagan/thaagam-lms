from django import forms
from accounts.models import User
from .models import School, GlobalCourse, GlobalConcept, GlobalConceptVideo


class SchoolForm(forms.ModelForm):
    admin_name     = forms.CharField(max_length=150, label='Admin Name')
    admin_email    = forms.EmailField(label='Admin Email')
    admin_password = forms.CharField(widget=forms.PasswordInput, label='Admin Password')

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
    class Meta:
        model  = GlobalConcept
        fields = ['header', 'h3_course', 'level', 'pdf', 'quiz', 'assignment']  # added level
        widgets = {
            'quiz':       forms.Textarea(attrs={'rows': 4}),
            'assignment': forms.Textarea(attrs={'rows': 4}),
        }