from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserProfile


def get_user_profile(user):
    """Safely get or create a UserProfile for any authenticated user."""
    default_role = 'operator' if (user.is_superuser or user.is_staff) else 'buyer'
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': default_role})
    return profile


def operator_required(view_func):
    """
    Decorator to restrict access to Operators and Superusers/Staff only.
    Non-operators (e.g. Buyers) attempting to access will receive a 403 PermissionDenied.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if request.user.is_superuser or request.user.is_staff or profile.role == 'operator':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Access restricted. Operator privileges required.")
    return _wrapped_view


def buyer_required(view_func):
    """
    Decorator to restrict access to Buyers (and Superusers for inspection).
    Operators are prevented from acting as buyers unless superuser.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if profile.role == 'buyer' or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Access restricted. Buyer account required.")
    return _wrapped_view

