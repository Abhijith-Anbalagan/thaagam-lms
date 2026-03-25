from django import forms
from .models import Classroom


class ClassroomForm(forms.ModelForm):
    class Meta:
        model   = Classroom
        fields  = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Mathematics Grade 10 — Section A',
                'autofocus': True,
            })
        }

# NOTE: CourseContentForm removed.
# Teachers are view-only for course content.
# Course content is created/managed by the Super Admin (Member 2).
# The CourseContent model still exists in models.py for DB structure —
# it is only written to by the admin, read by both teachers and students.
