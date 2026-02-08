"""
Views for task management, dashboards, analytics, search, and exports.
"""
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .decorators import team_leader_required
from .forms import (
    TaskAttachmentForm,
    TaskCommentForm,
    TaskFilterForm,
    TaskForm,
    TaskStatusForm,
)
from .models import (
    CustomUser,
    Notification,
    NotificationPreference,
    Task,
    TaskActivity,
    TaskAttachment,
    TaskComment,
    Team,
    TeamMembership,
)


def _get_notification_preferences(user: CustomUser) -> NotificationPreference | None:
    """
    Helper to safely get notification preferences for a user.
    """
    try:
        return user.notification_preferences
    except NotificationPreference.DoesNotExist:  # pragma: no cover - safety net
        return None


def _should_send_notification_email(pref: NotificationPreference | None, notification_type: str) -> bool:
    """
    Check whether an email should be sent for a given notification type.
    """
    if pref is None or not pref.email_notifications:
        return False

    mapping = {
        'task_assigned': pref.task_assigned,
        'status_changed': pref.status_changed,
        'comment_added': pref.comment_added,
        'deadline_approaching': pref.deadline_approaching,
        'task_overdue': pref.task_overdue,
    }
    return mapping.get(notification_type, False)


def create_notification(recipient: CustomUser, notification_type: str, message: str, task: Task | None = None) -> Notification:
    """
    Create an in-app notification respecting user preferences (for email decisions).
    """
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        message=message,
        task=task,
    )

    # Optionally send email based on preferences
    pref = _get_notification_preferences(recipient)
    if _should_send_notification_email(pref, notification_type):
        subject = f"[Team Todo] {notification.get_notification_type_display()}"
        body_lines = [message]
        if task:
            body_lines.append(f"\nTask: {task.title}")
        body_lines.append("\n\nLog in to Team Todo to view more details.")
        send_mail(
            subject=subject,
            message="".join(body_lines),
            from_email=None,
            recipient_list=[recipient.email],
            fail_silently=True,
        )

    return notification


def log_task_activity(
    *,
    task: Task,
    user: CustomUser,
    activity_type: str,
    description: str,
    old_value: str = "",
    new_value: str = "",
) -> TaskActivity:
    """
    Helper to record task activity history.
    """
    return TaskActivity.objects.create(
        task=task,
        user=user,
        activity_type=activity_type,
        description=description,
        old_value=old_value,
        new_value=new_value,
    )


def is_team_member_or_leader(user, team):
    """Check if user is a member or leader of the team."""
    return team.has_member(user) or user.is_admin


def is_task_accessible(user, task):
    """Check if user can access this task."""
    return (
        is_team_member_or_leader(user, task.team) or
        user.is_admin
    )


@login_required
@require_http_methods(['GET'])
def task_list(request, team_id):
    """
    List all tasks in a team with filtering and search.
    
    Accessible by team leaders and members.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)
    
    # Check access
    if not is_team_member_or_leader(request.user, team):
        messages.error(request, 'You do not have access to this team.')
        return redirect('users:team_list')
    
    # Get all tasks for the team
    tasks = Task.objects.filter(team=team).select_related(
        'created_by', 'assigned_to', 'team'
    ).prefetch_related('comments', 'attachments')
    
    # Initialize filter form
    filter_form = TaskFilterForm(team=team, data=request.GET if request.GET else None)
    
    # Apply filters
    if filter_form.is_valid():
        # Status filter
        status = filter_form.cleaned_data.get('status')
        if status:
            tasks = tasks.filter(status__in=status)
        
        # Priority filter
        priority = filter_form.cleaned_data.get('priority')
        if priority:
            tasks = tasks.filter(priority__in=priority)
        
        # Assignee filter
        assigned_to = filter_form.cleaned_data.get('assigned_to')
        if assigned_to:
            tasks = tasks.filter(assigned_to=assigned_to)
        
        # Search filter
        search = filter_form.cleaned_data.get('search')
        if search:
            tasks = tasks.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Sorting
        sort_by = filter_form.cleaned_data.get('sort_by')
        if sort_by:
            tasks = tasks.order_by(sort_by)
    else:
        tasks = tasks.order_by('-due_date')
    
    # Get statistics
    total_tasks = Task.objects.filter(team=team).count()
    completed_tasks = tasks.filter(status='completed').count()
    in_progress_tasks = tasks.filter(status='in_progress').count()
    overdue_tasks = tasks.filter(
        due_date__lt=timezone.now(),
        status__in=['not_started', 'in_progress', 'review']
    ).count()
    
    can_create_task = team.is_leader(request.user) or request.user.is_admin()
    context = {
        'team': team,
        'tasks': tasks,
        'filter_form': filter_form,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'can_create_task': can_create_task,
    }
    
    return render(request, 'tasks/task_list.html', context)


@login_required
@team_leader_required
@require_http_methods(['GET', 'POST'])
def task_create(request, team_id):
    """
    Create a new task in a team.
    
    Only accessible by team leaders.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)
    
    # Check if user is the team leader
    if not (team.is_leader(request.user) or request.user.is_admin):
        messages.error(request, 'Only team leaders can create tasks.')
        return redirect('users:team_detail', team_id=team_id)
    
    if request.method == 'POST':
        form = TaskForm(team=team, data=request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.team = team
            task.created_by = request.user
            task.save()

            # Log activity
            log_task_activity(
                task=task,
                user=request.user,
                activity_type='created',
                description=f'Task "{task.title}" created.',
            )

            # Notify assignee if any
            if task.assigned_to and task.assigned_to != request.user:
                create_notification(
                    recipient=task.assigned_to,
                    notification_type='task_assigned',
                    message=f'You have been assigned to task "{task.title}" in team "{team.name}".',
                    task=task,
                )

            messages.success(request, f'Task "{task.title}" created successfully.')
            return redirect('users:task_detail', team_id=team_id, task_id=task.pk)
    else:
        form = TaskForm(team=team)
    
    context = {
        'form': form,
        'team': team,
        'action': 'Create Task',
    }
    
    return render(request, 'tasks/task_form.html', context)


@login_required
@require_http_methods(['GET'])
def task_detail(request, team_id, task_id):
    """
    View detailed task information with comments and attachments.
    
    Accessible by team members and leaders.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)
    task = get_object_or_404(Task, pk=task_id, team=team)
    
    # Check access
    if not is_task_accessible(request.user, task):
        messages.error(request, 'You do not have access to this task.')
        return redirect('users:team_list')
    
    comments = task.comments.select_related('user').order_by('-created_at')
    attachments = task.attachments.select_related('uploaded_by')
    
    # Get status choices for the quick update form
    status_choices = Task._meta.get_field('status').choices
    
    # Process tags: split by comma and strip whitespace
    tags = [tag.strip() for tag in task.tags.split(',') if tag.strip()] if task.tags else []
    
    # Initialize comment form for team members
    can_comment = is_team_member_or_leader(request.user, team)
    comment_form = TaskCommentForm() if can_comment else None
    
    context = {
        'team': team,
        'task': task,
        'comments': comments,
        'attachments': attachments,
        'can_edit': task.created_by == request.user or request.user.is_admin,
        'can_comment': can_comment,
        'is_overdue': task.is_overdue(),
        'status_choices': status_choices,
        'tags': tags,
        'form': comment_form,
    }
    
    return render(request, 'tasks/task_detail.html', context)


@login_required
@team_leader_required
@require_http_methods(['GET', 'POST'])
def task_edit(request, team_id, task_id):
    """
    Edit an existing task.
    
    Only accessible by task creator or admin.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)
    task = get_object_or_404(Task, pk=task_id, team=team)
    
    # Check if user can edit
    if not (task.created_by == request.user or request.user.is_admin):
        messages.error(request, 'You can only edit your own tasks.')
        return redirect('users:task_detail', team_id=team_id, task_id=task_id)
    
    if request.method == 'POST':
        # Capture old values for activity logging
        old_status = task.get_status_display()
        old_priority = task.get_priority_display() if hasattr(task, 'get_priority_display') else task.priority
        old_assignee = task.assigned_to

        form = TaskForm(team=team, data=request.POST, instance=task)
        if form.is_valid():
            task = form.save()

            # Detect and log changes
            if old_status != task.get_status_display():
                log_task_activity(
                    task=task,
                    user=request.user,
                    activity_type='status_changed',
                    description=f'Status changed from {old_status} to {task.get_status_display()}.',
                    old_value=old_status,
                    new_value=task.get_status_display(),
                )

                # Notify assignee and creator when moving to review/completed
                if task.status in ['review', 'completed']:
                    recipients = set()
                    if task.assigned_to and task.assigned_to != request.user:
                        recipients.add(task.assigned_to)
                    if task.created_by and task.created_by != request.user:
                        recipients.add(task.created_by)

                    for recipient in recipients:
                        create_notification(
                            recipient=recipient,
                            notification_type='status_changed',
                            message=(
                                f'Status for task "{task.title}" in team "{task.team.name}" '
                                f'changed to {task.get_status_display()}.'
                            ),
                            task=task,
                        )

            if old_priority != task.get_priority_display():
                log_task_activity(
                    task=task,
                    user=request.user,
                    activity_type='priority_changed',
                    description=f'Priority changed from {old_priority} to {task.get_priority_display()}.',
                    old_value=old_priority,
                    new_value=task.get_priority_display(),
                )

            if old_assignee != task.assigned_to:
                old_assignee_name = old_assignee.get_display_name() if old_assignee else 'Unassigned'
                new_assignee_name = task.assigned_to.get_display_name() if task.assigned_to else 'Unassigned'
                log_task_activity(
                    task=task,
                    user=request.user,
                    activity_type='assigned',
                    description=f'Assignment changed from {old_assignee_name} to {new_assignee_name}.',
                    old_value=old_assignee_name,
                    new_value=new_assignee_name,
                )

                # Notify newly assigned user
                if task.assigned_to and task.assigned_to != request.user:
                    create_notification(
                        recipient=task.assigned_to,
                        notification_type='task_assigned',
                        message=f'You have been assigned to task "{task.title}" in team "{team.name}".',
                        task=task,
                    )

            messages.success(request, f'Task "{task.title}" updated successfully.')
            return redirect('users:task_detail', team_id=team_id, task_id=task.pk)
    else:
        form = TaskForm(team=team, instance=task)
    
    context = {
        'form': form,
        'team': team,
        'task': task,
        'action': 'Edit Task',
    }
    
    return render(request, 'tasks/task_form.html', context)


@login_required
@team_leader_required
@require_http_methods(['POST'])
def task_delete(request, team_id, task_id):
    """
    Delete a task (soft delete).
    
    Only accessible by task creator or admin.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)
    task = get_object_or_404(Task, pk=task_id, team=team)
    
    # Check if user can delete
    if not (task.created_by == request.user or request.user.is_admin):
        messages.error(request, 'You can only delete your own tasks.')
        return redirect('users:task_detail', team_id=team_id, task_id=task_id)
    
    task_title = task.title
    task.delete()
    messages.success(request, f'Task "{task_title}" deleted successfully.')
    return redirect('users:task_list', team_id=team_id)


@login_required
@require_http_methods(['POST'])
def task_update_status(request, team_id, task_id):
    """
    Update task status (for quick status changes).
    
    Members can update status of assigned tasks.
    Leaders can update any task status.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)
    task = get_object_or_404(Task, pk=task_id, team=team)
    
    # Check access
    if not is_task_accessible(request.user, task):
        messages.error(request, 'You do not have access to this task.')
        return redirect('users:team_list')
    
    # Check if user can update status
    can_update = (
        task.assigned_to == request.user or
        task.created_by == request.user or
        request.user.is_admin
    )
    
    if not can_update:
        messages.error(request, 'You do not have permission to update this task status.')
        return redirect('users:task_detail', team_id=team_id, task_id=task_id)
    
    form = TaskStatusForm(data=request.POST)
    if form.is_valid():
        old_status_display = task.get_status_display()
        old_status = task.status
        new_status = form.cleaned_data['status']
        task.status = new_status
        task.save()

        # Log activity
        log_task_activity(
            task=task,
            user=request.user,
            activity_type='status_changed',
            description=f'Status changed from {old_status_display} to {task.get_status_display()}.',
            old_value=old_status_display,
            new_value=task.get_status_display(),
        )

        # Notify assignee and creator when moving to review/completed
        if new_status in ['review', 'completed']:
            recipients = set()
            if task.assigned_to and task.assigned_to != request.user:
                recipients.add(task.assigned_to)
            if task.created_by and task.created_by != request.user:
                recipients.add(task.created_by)

            for recipient in recipients:
                create_notification(
                    recipient=recipient,
                    notification_type='status_changed',
                    message=(
                        f'Status for task "{task.title}" in team "{task.team.name}" '
                        f'changed to {task.get_status_display()}.'
                    ),
                    task=task,
                )

        messages.success(
            request,
            f'Task status changed from {old_status_display} to {task.get_status_display()}.'
        )
    
    return redirect('users:task_detail', team_id=team_id, task_id=task_id)


@login_required
@require_http_methods(['POST'])
def task_add_comment(request, team_id, task_id):
    """
    Add a comment to a task.
    
    Accessible by team members and leaders.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)
    task = get_object_or_404(Task, pk=task_id, team=team)
    
    # Check access
    if not is_team_member_or_leader(request.user, team):
        messages.error(request, 'You do not have access to this team.')
        return redirect('users:team_list')
    
    form = TaskCommentForm(data=request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.user = request.user
        comment.save()

        # Log activity
        log_task_activity(
            task=task,
            user=request.user,
            activity_type='commented',
            description='New comment added to task.',
            new_value=comment.comment,
        )

        # Notify task owner/assignee (excluding commenter)
        recipients = set()
        if task.assigned_to and task.assigned_to != request.user:
            recipients.add(task.assigned_to)
        if task.created_by and task.created_by != request.user:
            recipients.add(task.created_by)

        for recipient in recipients:
            create_notification(
                recipient=recipient,
                notification_type='comment_added',
                message=(
                    f'{request.user.get_display_name()} commented on task "{task.title}" '
                    f'in team "{team.name}".'
                ),
                task=task,
            )

        messages.success(request, 'Comment added successfully.')
    else:
        messages.error(request, 'Error adding comment.')
    
    return redirect('users:task_detail', team_id=team_id, task_id=task_id)


@login_required
@require_http_methods(['POST'])
def task_upload_attachment(request, team_id, task_id):
    """
    Upload an attachment to a task.
    
    Accessible by team members and leaders.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)
    task = get_object_or_404(Task, pk=task_id, team=team)
    
    # Check access
    if not is_team_member_or_leader(request.user, team):
        messages.error(request, 'You do not have access to this team.')
        return redirect('users:team_list')
    
    form = TaskAttachmentForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.task = task
        attachment.uploaded_by = request.user
        attachment.save()

        # Log activity
        log_task_activity(
            task=task,
            user=request.user,
            activity_type='attachment_added',
            description=f'Attachment "{attachment.filename}" uploaded.',
            new_value=attachment.filename,
        )

        messages.success(request, 'Attachment uploaded successfully.')
    else:
        messages.error(request, 'Error uploading attachment.')
    
    return redirect('users:task_detail', team_id=team_id, task_id=task_id)


@login_required
@require_http_methods(['GET'])
def my_tasks(request):
    """
    View tasks assigned to the current user.
    
    Shows a personalized dashboard for team members.
    """
    # Get tasks assigned to the user
    assigned_tasks = Task.objects.filter(
        assigned_to=request.user,
        team__is_active=True
    ).select_related(
        'team', 'created_by', 'assigned_to'
    ).prefetch_related('comments')
    
    # Get tasks created by the user
    created_tasks = Task.objects.filter(
        created_by=request.user,
        team__is_active=True
    ).select_related(
        'team', 'created_by', 'assigned_to'
    ).prefetch_related('comments')
    
    # Statistics
    total_assigned = assigned_tasks.count()
    completed = assigned_tasks.filter(status='completed').count()
    in_progress = assigned_tasks.filter(status='in_progress').count()
    overdue = assigned_tasks.filter(
        due_date__lt=timezone.now(),
        status__in=['not_started', 'in_progress', 'review']
    ).count()
    
    # Get teams the user is part of
    user_teams = Team.objects.filter(
        Q(leader=request.user) |
        Q(members__member=request.user),
        is_active=True
    ).distinct()
    
    context = {
        'assigned_tasks': assigned_tasks.order_by('-due_date'),
        'created_tasks': created_tasks.order_by('-created_at'),
        'total_assigned': total_assigned,
        'completed': completed,
        'in_progress': in_progress,
        'overdue': overdue,
        'user_teams': user_teams,
    }
    
    return render(request, 'tasks/my_tasks.html', context)


@login_required
def dashboard_redirect(request):
    """
    Role-based redirect to appropriate dashboard.
    """
    if request.user.is_team_leader() or request.user.is_admin():
        return redirect('users:dashboard_leader')
    return redirect('users:dashboard_member')


@login_required
def leader_dashboard(request):
    """
    Team leader dashboard with overview stats, charts, and activity.
    """
    user = request.user

    if not (user.is_team_leader() or user.is_admin()):
        return redirect('users:dashboard_member')

    # Teams this leader/admin can see
    if user.is_admin():
        teams = Team.objects.filter(is_active=True)
    else:
        teams = Team.objects.filter(leader=user, is_active=True)

    tasks_qs = Task.objects.filter(team__in=teams).select_related(
        'team', 'assigned_to', 'created_by'
    )

    now = timezone.now()
    week_ahead = now + timedelta(days=7)

    # Overview stats
    total_tasks = tasks_qs.count()
    status_counts = tasks_qs.values('status').annotate(count=Count('id'))
    overdue_count = tasks_qs.filter(
        due_date__lt=now,
        status__in=['not_started', 'in_progress', 'review'],
    ).count()
    due_this_week_count = tasks_qs.filter(
        due_date__gte=now,
        due_date__lte=week_ahead,
        status__in=['not_started', 'in_progress', 'review'],
    ).count()

    # Tasks by priority (for pie chart)
    priority_counts = list(
        tasks_qs.values('priority').annotate(count=Count('id')).order_by('priority')
    )

    # Completion trend last 30 days (line chart)
    last_30_days = now - timedelta(days=30)
    completion_qs = (
        tasks_qs.filter(
            status='completed',
            updated_at__gte=last_30_days,
        )
        .annotate(day=TruncDate('updated_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    completion_trend = list(completion_qs)

    # Workload per member (bar chart)
    workload_qs = (
        tasks_qs.exclude(assigned_to__isnull=True)
        .values('assigned_to', 'assigned_to__first_name', 'assigned_to__last_name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    workload = list(workload_qs)

    # Recent activity (latest 10)
    recent_activities = (
        TaskActivity.objects.filter(task__team__in=teams)
        .select_related('task', 'user')
        .order_by('-created_at')[:10]
    )

    recent_comments = (
        TaskComment.objects.filter(task__team__in=teams)
        .select_related('task', 'user')
        .order_by('-created_at')[:10]
    )

    new_assignments = (
        TaskActivity.objects.filter(
            task__team__in=teams,
            activity_type='assigned',
        )
        .select_related('task', 'user')
        .order_by('-created_at')[:10]
    )

    # Upcoming deadlines (next 7 days)
    upcoming_deadlines = tasks_qs.filter(
        due_date__gte=now,
        due_date__lte=week_ahead,
        status__in=['not_started', 'in_progress', 'review'],
    ).order_by('due_date')[:20]

    context = {
        'teams': teams,
        'total_tasks': total_tasks,
        'status_counts': status_counts,
        'overdue_count': overdue_count,
        'due_this_week_count': due_this_week_count,
        'priority_counts_json': json.dumps(list(priority_counts), default=str),
        'completion_trend_json': json.dumps(completion_trend, default=str),
        'workload_json': json.dumps(workload, default=str),
        'recent_activities': recent_activities,
        'recent_comments': recent_comments,
        'new_assignments': new_assignments,
        'upcoming_deadlines': upcoming_deadlines,
    }

    return render(request, 'dashboard/leader_dashboard.html', context)


@login_required
def member_dashboard(request):
    """
    Team member dashboard with personal stats, tasks by status, and calendar.
    """
    user = request.user

    assigned_tasks = Task.objects.filter(
        assigned_to=user,
        team__is_active=True,
    ).select_related('team', 'created_by', 'assigned_to')

    now = timezone.now()
    start_week = now - timedelta(days=7)

    # Personal stats
    my_total_tasks = assigned_tasks.count()
    completed_this_week = assigned_tasks.filter(
        status='completed',
        updated_at__gte=start_week,
    ).count()
    in_progress_count = assigned_tasks.filter(status='in_progress').count()
    overdue_count = assigned_tasks.filter(
        due_date__lt=now,
        status__in=['not_started', 'in_progress', 'review'],
    ).count()

    # Tasks grouped by status
    tasks_by_status = {
        key: list(
            assigned_tasks.filter(status=key).order_by('due_date', '-created_at')[:20]
        )
        for key, _ in Task.STATUS_CHOICES
    }

    # Calendar events for FullCalendar (assigned tasks)
    calendar_events = []
    for task in assigned_tasks.exclude(due_date__isnull=True):
        calendar_events.append(
            {
                'id': task.id,
                'title': task.title,
                'start': task.due_date.isoformat(),
                'url': redirect(
                    'users:task_detail',
                    team_id=task.team_id,
                    task_id=task.id,
                ).url,
                'status': task.status,
                'priority': task.priority,
            }
        )

    # Recent items
    recently_assigned = assigned_tasks.order_by('-created_at')[:10]
    recent_comments = (
        TaskComment.objects.filter(task__assigned_to=user)
        .select_related('task', 'user')
        .order_by('-created_at')[:10]
    )

    context = {
        'my_total_tasks': my_total_tasks,
        'completed_this_week': completed_this_week,
        'in_progress_count': in_progress_count,
        'overdue_count': overdue_count,
        'tasks_by_status': tasks_by_status,
        'calendar_events_json': json.dumps(calendar_events, default=str),
        'recently_assigned': recently_assigned,
        'recent_comments': recent_comments,
    }

    return render(request, 'dashboard/member_dashboard.html', context)


@login_required
def team_analytics(request, team_id):
    """
    Team performance analytics for leaders/admins.
    """
    team = get_object_or_404(Team, pk=team_id, is_active=True)

    if not (team.is_leader(request.user) or request.user.is_admin()):
        messages.error(request, 'You do not have permission to view analytics for this team.')
        return redirect('users:team_detail', pk=team_id)

    # Date range selector
    try:
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        if start_str and end_str:
            start_date = timezone.datetime.fromisoformat(start_str)
            end_date = timezone.datetime.fromisoformat(end_str)
        else:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
    except ValueError:
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

    tasks_qs = Task.objects.filter(
        team=team,
        created_at__gte=start_date,
        created_at__lte=end_date,
    ).select_related('assigned_to', 'created_by')

    # Tasks completed over time
    completed_qs = (
        tasks_qs.filter(status='completed', updated_at__gte=start_date, updated_at__lte=end_date)
        .annotate(day=TruncDate('updated_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    completed_trend = list(completed_qs)

    # Average completion time (approx using updated_at - created_at)
    completed_tasks = tasks_qs.filter(status='completed', updated_at__isnull=False)
    total_seconds = 0
    completed_count = completed_tasks.count()
    for t in completed_tasks:
        delta = (t.updated_at - t.created_at).total_seconds()
        if delta > 0:
            total_seconds += delta
    avg_completion_hours = (total_seconds / completed_count / 3600) if completed_count else 0

    # Tasks by priority distribution
    priority_distribution = list(
        tasks_qs.values('priority').annotate(count=Count('id')).order_by('priority')
    )

    # Member productivity (tasks completed per member)
    member_productivity = list(
        completed_tasks.values(
            'assigned_to',
            'assigned_to__first_name',
            'assigned_to__last_name',
        )
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    context = {
        'team': team,
        'start_date': start_date,
        'end_date': end_date,
        'completed_trend_json': json.dumps(completed_trend, default=str),
        'avg_completion_hours': round(avg_completion_hours, 2),
        'priority_distribution_json': json.dumps(priority_distribution, default=str),
        'member_productivity': member_productivity,
    }

    return render(request, 'analytics/team_analytics.html', context)


@login_required
def personal_stats(request):
    """
    Personal statistics and productivity analytics for current user.
    """
    user = request.user
    now = timezone.now()
    start_30 = now - timedelta(days=30)
    start_week = now - timedelta(days=7)

    tasks_qs = Task.objects.filter(
        assigned_to=user,
        team__is_active=True,
    )

    # Counts
    completed_this_week = tasks_qs.filter(
        status='completed',
        updated_at__gte=start_week,
    ).count()

    completed_this_month = tasks_qs.filter(
        status='completed',
        updated_at__gte=start_30,
    ).count()

    total_in_period = tasks_qs.filter(created_at__gte=start_30).count()
    completion_rate = (completed_this_month / total_in_period * 100) if total_in_period else 0

    # Average tasks per day (last 30 days)
    avg_tasks_per_day = completed_this_month / 30 if completed_this_month else 0

    # Productivity chart: completions over last 30 days
    productivity_qs = (
        tasks_qs.filter(
            status='completed',
            updated_at__gte=start_30,
        )
        .annotate(day=TruncDate('updated_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    productivity_trend = list(productivity_qs)

    context = {
        'completed_this_week': completed_this_week,
        'completed_this_month': completed_this_month,
        'avg_tasks_per_day': round(avg_tasks_per_day, 2),
        'completion_rate': round(completion_rate, 1),
        'productivity_trend_json': json.dumps(productivity_trend, default=str),
    }

    return render(request, 'analytics/personal_stats.html', context)


@login_required
def export_tasks_csv(request):
    """
    Export tasks to CSV.

    - If team_id provided and user is leader/admin of that team: export team tasks.
    - Otherwise, export personal assigned tasks.
    """
    import csv

    team_id = request.GET.get('team_id')

    if team_id:
        team = get_object_or_404(Team, pk=team_id)
        if not (team.is_leader(request.user) or request.user.is_admin()):
            messages.error(request, 'You do not have permission to export tasks for this team.')
            return redirect('users:team_detail', pk=team_id)
        tasks_qs = Task.objects.filter(team=team)
        filename = f"team_{team.id}_tasks.csv"
    else:
        tasks_qs = Task.objects.filter(assigned_to=request.user, team__is_active=True)
        filename = f"user_{request.user.id}_tasks.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            'ID',
            'Title',
            'Team',
            'Created By',
            'Assigned To',
            'Priority',
            'Status',
            'Due Date',
            'Tags',
            'Created At',
            'Updated At',
        ]
    )

    for t in tasks_qs.select_related('team', 'created_by', 'assigned_to'):
        writer.writerow(
            [
                t.id,
                t.title,
                t.team.name,
                t.created_by.get_display_name(),
                t.assigned_to.get_display_name() if t.assigned_to else '',
                t.get_priority_display(),
                t.get_status_display(),
                t.due_date.isoformat() if t.due_date else '',
                t.tags,
                t.created_at.isoformat(),
                t.updated_at.isoformat(),
            ]
        )

    return response


@login_required
def export_personal_tasks_pdf(request):
    """
    Export current user's tasks to a simple PDF report.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    tasks_qs = Task.objects.filter(
        assigned_to=request.user,
        team__is_active=True,
    ).select_related('team')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="my_tasks.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont('Helvetica-Bold', 14)
    p.drawString(50, y, f"My Tasks Report - {request.user.get_display_name()}")
    y -= 30
    p.setFont('Helvetica', 10)

    for t in tasks_qs.order_by('due_date', '-created_at'):
        if y < 80:
            p.showPage()
            y = height - 50
            p.setFont('Helvetica', 10)

        line = f"[{t.get_status_display()}] {t.title} (Team: {t.team.name})"
        p.drawString(50, y, line[:110])
        y -= 14
        if t.due_date:
            p.drawString(60, y, f"Due: {t.due_date.strftime('%Y-%m-%d %H:%M')}  Priority: {t.get_priority_display()}")
            y -= 14

    p.showPage()
    p.save()
    return response


@login_required
def search(request):
    """
    Global task search across teams the user can access.
    """
    from django.core.paginator import Paginator

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    priority = request.GET.get('priority', '').strip()

    tasks_qs = Task.objects.filter(team__is_active=True).select_related(
        'team', 'created_by', 'assigned_to'
    )

    # Restrict to teams this user can see
    if request.user.is_admin():
        pass
    else:
        teams = Team.objects.filter(
            Q(leader=request.user) | Q(members__member=request.user),
            is_active=True,
        ).distinct()
        tasks_qs = tasks_qs.filter(team__in=teams)

    if query:
        tasks_qs = tasks_qs.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    if status:
        tasks_qs = tasks_qs.filter(status=status)

    if priority:
        tasks_qs = tasks_qs.filter(priority=priority)

    tasks_qs = tasks_qs.order_by('-updated_at')

    paginator = Paginator(tasks_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'query': query,
        'status': status,
        'priority': priority,
        'page_obj': page_obj,
    }
    return render(request, 'search/results.html', context)
