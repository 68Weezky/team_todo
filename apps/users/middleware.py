"""
Middleware for role-based access control.
"""
from django.http import HttpResponseForbidden


class RoleCheckMiddleware:
    """
    Middleware to log and track role-based access attempts.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log role information if user is authenticated
        if request.user.is_authenticated:
            request.user_role = request.user.role
        
        response = self.get_response(request)
        return response
