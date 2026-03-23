from django import forms
from .models import Classroom, CourseContent


class ClassroomForm(forms.ModelForm):
    class Meta:
        model  = Classroom
        fields = ['name']


class CourseContentForm(forms.ModelForm):
    class Meta:
        model  = CourseContent
        fields = ['title', 'content_type', 'unit', 'video_url', 'file']
