from django import forms

class InviteForm(forms.Form):
    email = forms.EmailField()
