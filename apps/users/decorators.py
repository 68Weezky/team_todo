"""
Decorators for role-based access control.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def team_leader_required(view_func):
    """
    Decorator to restrict view access to team leaders and admins.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ['team_leader', 'admin']:
            return HttpResponseForbidden(
                'You do not have permission to access this page. Team leader access required.'
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def team_member_required(view_func):
    """
    Decorator to restrict view access to team members, team leaders, and admins.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ['team_member', 'team_leader', 'admin']:
            return HttpResponseForbidden(
                'You do not have permission to access this page. Team member access required.'
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """
    Decorator to restrict view access to admins only.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            return HttpResponseForbidden(
                'You do not have permission to access this page. Admin access required.'
            )
        return view_func(request, *args, **kwargs)
    return wrapper
