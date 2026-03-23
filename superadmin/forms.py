from django import forms
from .models import School, GlobalCourse


class SchoolForm(forms.ModelForm):
    class Meta:
        model  = School
        fields = ['name', 'address']


class SchoolAdminForm(forms.Form):
    school   = forms.ModelChoiceField(queryset=School.objects.filter(is_active=True))
    email    = forms.EmailField()
    password = forms.CharField(widget=forms.TextInput)


class GlobalCourseForm(forms.ModelForm):
    class Meta:
        model  = GlobalCourse
        fields = ['title', 'content', 'school', 'status']
