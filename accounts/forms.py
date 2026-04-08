from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import User
from .models import Testimonial




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

    # ← REPLACE YOUR EXISTING clean() WITH THIS
    def clean(self):
        cleaned_data = super().clean()
        email    = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                raise forms.ValidationError(self.error_messages['invalid_login'])

            # Skip email verification check for admin/staff users
            if not user.is_superuser and not user.is_staff:
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
        fields = ['username', 'avatar']



class PasswordChangeCustomForm(PasswordChangeForm):
    pass


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email'
        })
    )


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'New Password'}),
        label='New Password'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm New Password'}),
        label='Confirm New Password'
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data
    
    



class TestimonialForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f"{i} ★") for i in range(1, 6)],
        widget=forms.RadioSelect
    )

    class Meta:
        model = Testimonial
        fields = ['name', 'email', 'message', 'rating']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your email (optional)'}),
            'message': forms.Textarea(attrs={'placeholder': 'Share your experience...', 'rows': 4}),
        }
