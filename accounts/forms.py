from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import User



# ─── Signup ───────────────────────────────────────────────────────────────────

class SignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    class Meta:
        model  = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email

    def clean(self):
        cd = super().clean()
        if cd.get('password1') != cd.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return cd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = 'public'
        user.is_active = False
        user.email_verified = False
        if commit:
            user.save()
        return user




# ─── Login ────────────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    email    = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    error_messages = {
        'invalid_login': 'Please enter a correct email and password.',
        'inactive':      'Your account is not active. Please verify your email first.',
    }

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email    = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                raise forms.ValidationError(self.error_messages['invalid_login'])

            if not user.is_active or not user.email_verified:
               raise forms.ValidationError(
                     f'Your email is not verified. '
                     f'<a href="/resend-verification/?email={user.email}">Click here to resend verification email.</a>'
    )

            self.user = authenticate(request=None, email=email, password=password)
            if self.user is None:
                raise forms.ValidationError(self.error_messages['invalid_login'])

        return cleaned_data

    def get_user(self):
        return self.user


# ─── Accept Invite ────────────────────────────────────────────────────────────

class AcceptInviteForm(forms.Form):
    username  = forms.CharField(max_length=150)
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # username is NOT unique in your model — so no uniqueness check needed
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned
    


# ─── Profile ──────────────────────────────────────────────────────────────────

class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'avatar']


class PasswordChangeCustomForm(PasswordChangeForm):
    pass
