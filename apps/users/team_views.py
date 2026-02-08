"""
Views for team management functionality.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .models import Team, TeamMembership, CustomUser
from .forms import TeamForm, AddTeamMemberForm
from .decorators import team_leader_required


def is_team_leader_or_admin(user, team):
    """Check if user is the team leader or an admin."""
    return team.leader == user or user.is_admin()


@login_required
@require_http_methods(['GET', 'POST'])
def team_list(request):
    """
    List teams based on user role.
    - Team leaders see teams they lead
    - Members see teams they belong to
    - Admins see all teams
    """
    user = request.user
    
    if user.is_admin():
        teams = Team.objects.all()
    elif user.is_team_leader():
        # Show teams led by this user and teams they're members of
        teams = Team.objects.filter(
            Q(leader=user) | Q(members__member=user)
        ).distinct()
    else:
        # Team members see only teams they belong to
        teams = Team.objects.filter(members__member=user)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        teams = teams.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter active teams
    if not user.is_admin():
        teams = teams.filter(is_active=True)
    
    context = {
        'teams': teams,
        'search_query': search_query,
    }
    return render(request, 'teams/team_list.html', context)


@login_required
@team_leader_required
@require_http_methods(['GET', 'POST'])
def team_create(request):
    """
    Create a new team (team leaders and admins only).
    """
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.leader = request.user
            team.save()
            messages.success(request, f'Team "{team.name}" created successfully!')
            return redirect('users:team_detail', pk=team.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = TeamForm()
    
    context = {'form': form}
    return render(request, 'teams/team_form.html', context)


@login_required
@require_http_methods(['GET'])
def team_detail(request, pk):
    """
    Display team details and member list.
    Accessible to team members, team leaders, and admins.
    """
    team = get_object_or_404(Team, pk=pk)
    
    # Check if user has access to this team
    if not team.has_member(request.user) and not request.user.is_admin():
        messages.error(request, 'You do not have access to this team.')
        return redirect('users:team_list')
    
    # Get all members (including the leader)
    members = team.members.select_related('member').all()
    
    context = {
        'team': team,
        'members': members,
        'is_leader': is_team_leader_or_admin(request.user, team),
    }
    return render(request, 'teams/team_detail.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def team_edit(request, pk):
    """
    Edit team details (team leader of the team only).
    """
    team = get_object_or_404(Team, pk=pk)
    
    # Permission check
    if not is_team_leader_or_admin(request.user, team):
        messages.error(request, 'You do not have permission to edit this team.')
        return redirect('users:team_detail', pk=team.pk)
    
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            team = form.save()
            messages.success(request, f'Team "{team.name}" updated successfully!')
            return redirect('users:team_detail', pk=team.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = TeamForm(instance=team)
    
    context = {
        'form': form,
        'team': team,
        'is_edit': True,
    }
    return render(request, 'teams/team_form.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def team_delete(request, pk):
    """
    Delete a team (team leader only, with confirmation).
    """
    team = get_object_or_404(Team, pk=pk)
    
    # Permission check
    if not is_team_leader_or_admin(request.user, team):
        messages.error(request, 'You do not have permission to delete this team.')
        return redirect('users:team_detail', pk=team.pk)
    
    if request.method == 'POST':
        team_name = team.name
        team.delete()
        messages.success(request, f'Team "{team_name}" has been deleted.')
        return redirect('users:team_list')
    
    context = {'team': team}
    return render(request, 'teams/team_confirm_delete.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def manage_members(request, pk):
    """
    Manage team members (add/remove members).
    Only team leader or admin can access.
    """
    team = get_object_or_404(Team, pk=pk)
    
    # Permission check
    if not is_team_leader_or_admin(request.user, team):
        messages.error(request, 'You do not have permission to manage this team.')
        return redirect('users:team_detail', pk=team.pk)
    
    if request.method == 'POST':
        form = AddTeamMemberForm(team, request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                TeamMembership.objects.create(team=team, member=user)
                messages.success(
                    request,
                    f'{user.get_display_name()} has been added to the team.'
                )
                return redirect('users:manage_members', pk=team.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = AddTeamMemberForm(team)
    
    members = team.members.select_related('member').all()
    
    context = {
        'team': team,
        'form': form,
        'members': members,
    }
    return render(request, 'teams/manage_members.html', context)


@login_required
@require_http_methods(['POST'])
def remove_member(request, pk, user_id):
    """
    Remove a member from the team (team leader only).
    """
    team = get_object_or_404(Team, pk=pk)
    user = get_object_or_404(CustomUser, pk=user_id)
    
    # Permission check
    if not is_team_leader_or_admin(request.user, team):
        messages.error(request, 'You do not have permission to manage this team.')
        return redirect('users:team_detail', pk=team.pk)
    
    # Cannot remove team leader
    if user == team.leader:
        messages.error(request, 'You cannot remove the team leader.')
        return redirect('users:manage_members', pk=team.pk)
    
    # Remove the member
    TeamMembership.objects.filter(team=team, member=user).delete()
    messages.success(request, f'{user.get_display_name()} has been removed from the team.')
    
    return redirect('users:manage_members', pk=team.pk)


@login_required
@require_http_methods(['POST'])
def leave_team(request, pk):
    """
    Allow a member to leave a team.
    Cannot leave if you're the team leader.
    """
    team = get_object_or_404(Team, pk=pk)
    
    # Cannot leave if you're the team leader
    if team.leader == request.user:
        messages.error(request, 'Team leaders cannot leave their own team.')
        return redirect('users:team_detail', pk=team.pk)
    
    # Remove membership
    TeamMembership.objects.filter(team=team, member=request.user).delete()
    messages.success(request, f'You have left the team "{team.name}".')
    
    return redirect('users:team_list')
