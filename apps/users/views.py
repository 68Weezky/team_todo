"""
Views for user authentication and profile management.
"""
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.urls import reverse_lazy
from .models import CustomUser, Team, TeamMembership, Task

logger = logging.getLogger(__name__)
from .forms import (
    CustomUserCreationForm,
    CustomUserChangeForm,
    UserLoginForm,
    CustomPasswordResetForm
)


def home(request):
    """
    Home page view with user statistics.
    """
    context = {}
    
    if request.user.is_authenticated:
        try:
            # Calculate team count based on user role
            if request.user.is_admin():
                team_count = Team.objects.filter(is_active=True).count()
            elif request.user.is_team_leader():
                led_teams = Team.objects.filter(leader=request.user, is_active=True).count()
                member_teams = TeamMembership.objects.filter(
                    member=request.user,
                    team__is_active=True
                ).exclude(team__leader=request.user).count()
                team_count = led_teams + member_teams
            else:
                team_count = TeamMembership.objects.filter(
                    member=request.user,
                    team__is_active=True
                ).count()
            context['user_team_count'] = team_count
        except Exception:
            context['user_team_count'] = 0

        try:
            active_tasks_count = Task.objects.filter(
                assigned_to=request.user,
                status__in=['not_started', 'in_progress', 'review'],
                team__is_active=True
            ).count()
            context['active_tasks_count'] = active_tasks_count
        except Exception:
            context['active_tasks_count'] = 0
    
    return render(request, 'home.html', context)


@require_http_methods(['GET', 'POST'])
def register(request):
    """
    User registration view.
    GET: Display registration form
    POST: Process registration and create new user
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(
                    request,
                    f'Account created successfully! Welcome {user.get_display_name()}.'
                )
                login(request, user)
                return redirect('home')
            except Exception as e:
                logger.exception('Registration failed: %s', e)
                messages.error(
                    request,
                    'Registration failed. Please try again or use a different email.'
                )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def login_view(request):
    """
    User login view using email and password.
    GET: Display login form
    POST: Authenticate user and create session
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')
            
            # Authenticate using username (which is set to email)
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                
                # Set session expiry based on remember_me
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires on browser close
                
                messages.success(request, f'Welcome back, {user.get_display_name()}!')
                
                # Redirect to next page if provided
                next_page = request.GET.get('next', 'home')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'registration/login.html', {'form': form})


@require_http_methods(['GET', 'POST'])
@login_required
def logout_view(request):
    """
    User logout view.
    Logs out user and redirects to login page.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('users:login')


@login_required
def profile(request):
    """
    User profile view.
    GET: Display user profile
    POST: Update user profile information
    """
    user = request.user
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserChangeForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'users/profile.html', context)


class TeamTodoPasswordResetView(PasswordResetView):
    """
    Custom password reset view using email.
    """
    form_class = CustomPasswordResetForm
    template_name = 'registration/password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')

    def form_valid(self, form):
        """Override to provide custom messaging."""
        messages.info(
            self.request,
            'Password reset link has been sent to your email address.'
        )
        return super().form_valid(form)


class TeamTodoPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Custom password reset confirm view.
    """
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        """Override to provide custom messaging."""
        messages.success(self.request, 'Password reset successfully! You can now login.')
        return super().form_valid(form)


@login_required
def user_list(request):
    """
    View to list all users (admin only).
    """
    if not request.user.is_admin():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    users = CustomUser.objects.all().order_by('-date_joined')
    
    context = {
        'users': users,
    }
    return render(request, 'users/user_list.html', context)
