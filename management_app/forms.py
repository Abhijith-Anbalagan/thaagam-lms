from django import forms
class InviteTeacherForm(forms.Form):
    email = forms.EmailField()
