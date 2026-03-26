from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(reverse('login'))
            if not request.user.is_superuser and request.user.role not in roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect(request.user.get_dashboard_url())
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator