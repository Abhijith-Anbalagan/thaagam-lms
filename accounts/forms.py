from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import User


class SignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'username', 'email', 'phone']

    def clean(self):
        cd = super().clean()
        if cd.get('password1') != cd.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return cd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = 'public'
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    pass


class AcceptInviteForm(forms.Form):
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    password1  = forms.CharField(widget=forms.PasswordInput, label='Set Password')
    password2  = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def clean(self):
        cd = super().clean()
        if cd.get('password1') != cd.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return cd


class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'avatar']


class PasswordChangeCustomForm(PasswordChangeForm):
    pass
