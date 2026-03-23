from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, Invitation
from .forms import SignupForm, LoginForm, AcceptInviteForm, ProfileForm


def signup_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('/public-dashboard/')
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(user.get_dashboard_url())
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('/login/')


@login_required
def public_dashboard(request):
    error = None
    if request.method == 'POST':
        code = request.POST.get('class_code', '').strip().upper()
        from classrooms.models import Classroom
        try:
            classroom = Classroom.objects.get(code=code)
            classroom.students.add(request.user)
            request.user.role   = 'student'
            request.user.school = classroom.school
            request.user.save()
            messages.success(request, f'You joined {classroom.name}!')
            return redirect('/student/dashboard/')
        except Classroom.DoesNotExist:
            error = 'Class code not found. Try again.'
    return render(request, 'accounts/public_dashboard.html', {'error': error})


def accept_invite_view(request, token):
    invitation = get_object_or_404(Invitation, token=token)
    if not invitation.is_valid:
        return render(request, 'accounts/invite_invalid.html', {'invitation': invitation})

    form = AcceptInviteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        base = invitation.email.split('@')[0]
        username, counter = base, 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{counter}'; counter += 1

        user = User.objects.create(
            username=username, email=invitation.email,
            first_name=cd['first_name'], last_name=cd['last_name'],
            role=invitation.role, school=invitation.school,
        )
        user.set_password(cd['password1'])
        user.save()
        invitation.accepted = True
        invitation.save()
        login(request, user)
        messages.success(request, f'Welcome, {user.first_name}!')
        return redirect(user.get_dashboard_url())

    return render(request, 'accounts/accept_invite.html', {
        'form': form, 'invitation': invitation
    })


@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'shared/profile_settings.html', {'form': form})
