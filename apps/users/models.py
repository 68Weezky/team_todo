"""
Custom User model for team collaboration with role-based access.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """
    Extended User model with additional fields for team collaboration.
    
    Roles:
    - admin: Full access to all features and user management
    - team_leader: Can create teams, manage team members, and delegate tasks
    - team_member: Can create and manage their own tasks, comment on tasks
    """
    
    ROLE_CHOICES = [
        ('admin', _('Administrator')),
        ('team_leader', _('Team Leader')),
        ('team_member', _('Team Member')),
    ]
    
    email = models.EmailField(unique=True, help_text=_('Primary email address'))
    profile_picture = models.ImageField(
        upload_to='profile_pictures/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text=_('User profile picture')
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='team_member',
        help_text=_('User role determines access level')
    )
    bio = models.TextField(blank=True, help_text=_('Short bio about the user'))
    phone = models.CharField(max_length=20, blank=True, help_text=_('Contact phone number'))
    is_active = models.BooleanField(default=True, help_text=_('User account active status'))
    
    # Timestamps
    date_joined = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def is_admin(self):
        """Check if user is an administrator."""
        return self.role == 'admin'
    
    def is_team_leader(self):
        """Check if user is a team leader."""
        return self.role == 'team_leader'
    
    def is_team_member(self):
        """Check if user is a team member."""
        return self.role == 'team_member'
    
    def get_display_name(self):
        """Get user's display name (full name or username)."""
        if self.get_full_name():
            return self.get_full_name()
        return self.username


class Team(models.Model):
    """
    Team model for managing group collaboration.
    
    A team is led by a team_leader and contains multiple members.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_('Team name (must be unique)')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Team description and purpose')
    )
    leader = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='led_teams',
        limit_choices_to={'role__in': ['team_leader', 'admin']},
        help_text=_('Team leader who created and manages the team')
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_('Active teams are visible to members')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Team')
        verbose_name_plural = _('Teams')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['leader']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} (Led by {self.leader.get_display_name()})"
    
    def get_member_count(self):
        """Get the total number of members including the leader."""
        return self.members.count() + 1
    
    def has_member(self, user):
        """Check if a user is a member of this team."""
        return self.members.filter(member=user).exists() or self.leader == user
    
    def is_leader(self, user):
        """Check if a user is the leader of this team."""
        return self.leader == user


class TeamMembership(models.Model):
    """
    Membership model linking users to teams.
    
    Tracks which users are members of which teams and when they joined.
    """
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='members',
        help_text=_('Team this membership belongs to')
    )
    member = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='team_memberships',
        help_text=_('User who is a member of the team')
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When user joined the team')
    )
    
    class Meta:
        verbose_name = _('Team Membership')
        verbose_name_plural = _('Team Memberships')
        unique_together = ('team', 'member')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['team', 'member']),
            models.Index(fields=['team']),
        ]
    
    def __str__(self):
        return f"{self.member.get_display_name()} → {self.team.name}"


class Task(models.Model):
    """
    Task model for team collaboration and project management.
    
    Tracks tasks within teams with priority, status, assignment, and deadlines.
    """
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('not_started', _('Not Started')),
        ('in_progress', _('In Progress')),
        ('review', _('Review')),
        ('completed', _('Completed')),
    ]
    
    title = models.CharField(
        max_length=200,
        help_text=_('Task title or name')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Detailed task description')
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text=_('Team this task belongs to')
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='created_tasks',
        help_text=_('Team leader who created this task')
    )
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        help_text=_('Team member this task is assigned to')
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text=_('Task priority level')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started',
        help_text=_('Current task status')
    )
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Task due date and time')
    )
    tags = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Comma-separated tags for organization')
    )
    is_urgent = models.BooleanField(
        default=False,
        help_text=_('Mark task as urgent/flagged')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['priority']),
            models.Index(fields=['team', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def is_overdue(self):
        """Check if task is overdue."""
        from django.utils import timezone
        return self.due_date and self.due_date < timezone.now() and self.status != 'completed'
    
    def get_priority_color(self):
        """Get color for priority badge."""
        color_map = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'dark',
        }
        return color_map.get(self.priority, 'secondary')


class TaskComment(models.Model):
    """
    Comments on tasks for team collaboration and discussion.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text=_('Task this comment belongs to')
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='task_comments',
        help_text=_('User who posted the comment')
    )
    comment = models.TextField(
        help_text=_('Comment text')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Task Comment')
        verbose_name_plural = _('Task Comments')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['task', 'created_at']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user.get_display_name()} on {self.task.title}"


class TaskAttachment(models.Model):
    """
    File attachments on tasks for sharing documents and resources.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='attachments',
        help_text=_('Task this attachment belongs to')
    )
    file = models.FileField(
        upload_to='task_attachments/%Y/%m/%d/',
        help_text=_('Attachment file')
    )
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='task_attachments',
        help_text=_('User who uploaded this file')
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Task Attachment')
        verbose_name_plural = _('Task Attachments')
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['task']),
            models.Index(fields=['uploaded_by']),
        ]

    def __str__(self):
        return f"Attachment: {self.file.name} on {self.task.title}"

    @property
    def filename(self):
        """Get just the filename."""
        return self.file.name.split('/')[-1]


class Notification(models.Model):
    """
    In-app notifications for users.

    Tracks notifications for task assignments, status changes, comments, and deadlines.
    """

    NOTIFICATION_TYPES = [
        ('task_assigned', _('Task Assigned')),
        ('status_changed', _('Status Changed')),
        ('comment_added', _('Comment Added')),
        ('deadline_approaching', _('Deadline Approaching')),
        ('task_overdue', _('Task Overdue')),
    ]

    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text=_('User who receives this notification')
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        help_text=_('Type of notification')
    )
    message = models.TextField(
        help_text=_('Notification message')
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related task (if applicable)')
    )
    is_read = models.BooleanField(
        default=False,
        help_text=_('Whether notification has been read')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['task']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.get_display_name()}: {self.get_notification_type_display()}"


class TaskActivity(models.Model):
    """
    Audit log for task changes and activity.

    Tracks all changes to tasks (status, priority, assignment, etc.)
    """

    ACTIVITY_TYPES = [
        ('created', _('Created')),
        ('status_changed', _('Status Changed')),
        ('priority_changed', _('Priority Changed')),
        ('assigned', _('Assigned')),
        ('commented', _('Commented')),
        ('attachment_added', _('Attachment Added')),
        ('edited', _('Edited')),
        ('deleted', _('Deleted')),
    ]

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='activity_log',
        help_text=_('Task this activity is associated with')
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='task_activities',
        help_text=_('User who performed this action')
    )
    activity_type = models.CharField(
        max_length=30,
        choices=ACTIVITY_TYPES,
        help_text=_('Type of activity')
    )
    description = models.TextField(
        help_text=_('Description of what changed')
    )
    old_value = models.TextField(
        blank=True,
        help_text=_('Previous value (for changes)')
    )
    new_value = models.TextField(
        blank=True,
        help_text=_('New value (for changes)')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Task Activity')
        verbose_name_plural = _('Task Activities')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', 'created_at']),
            models.Index(fields=['user']),
            models.Index(fields=['activity_type']),
        ]

    def __str__(self):
        return f"{self.get_activity_type_display()} on {self.task.title} by {self.user.get_display_name()}"


class NotificationPreference(models.Model):
    """
    User notification preferences.

    Tracks which types of notifications and delivery methods users prefer.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text=_('User this preference belongs to')
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text=_('Receive email notifications')
    )
    task_assigned = models.BooleanField(
        default=True,
        help_text=_('Notify when task is assigned')
    )
    status_changed = models.BooleanField(
        default=True,
        help_text=_('Notify when task status changes')
    )
    comment_added = models.BooleanField(
        default=True,
        help_text=_('Notify when comment is added to your task')
    )
    deadline_approaching = models.BooleanField(
        default=True,
        help_text=_('Notify when deadline is approaching (24 hours)')
    )
    task_overdue = models.BooleanField(
        default=True,
        help_text=_('Notify when task becomes overdue')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')

    def __str__(self):
        return f"Notification preferences for {self.user.get_display_name()}"
