"""
Django admin configuration for users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    CustomUser, Team, TeamMembership, Task, TaskComment, TaskAttachment,
    Notification, TaskActivity, NotificationPreference
)


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Admin interface for CustomUser model with enhanced role management.
    """
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'bio')}),
        (_('Profile'), {'fields': ('profile_picture',)}),
        (_('Roles and permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'date_updated')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    list_display = ('username', 'email', 'get_full_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    readonly_fields = ('date_joined', 'date_updated')
    
    def get_full_name(self, obj):
        """Display user's full name."""
        return obj.get_full_name() or obj.username
    
    get_full_name.short_description = _('Full name')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """
    Admin interface for Team model.
    """
    list_display = ('name', 'leader', 'get_member_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'leader')
    search_fields = ('name', 'description', 'leader__email')
    readonly_fields = ('created_at', 'updated_at', 'get_member_count')
    
    fieldsets = (
        (None, {'fields': ('name', 'description')}),
        (_('Management'), {'fields': ('leader', 'is_active')}),
        (_('Statistics'), {'fields': ('get_member_count',)}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
    )
    
    def get_member_count(self, obj):
        """Display the total member count."""
        return obj.get_member_count()
    
    get_member_count.short_description = _('Members')


class TeamMembershipInline(admin.TabularInline):
    """
    Inline admin interface for TeamMembership within Team admin.
    """
    model = TeamMembership
    extra = 0
    readonly_fields = ('date_joined',)
    fields = ('member', 'date_joined')
    raw_id_fields = ('member',)


# Update TeamAdmin to include inline memberships
TeamAdmin.inlines = [TeamMembershipInline]


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    """
    Admin interface for TeamMembership model.
    """
    list_display = ('get_team_name', 'get_member_name', 'get_member_email', 'date_joined')
    list_filter = ('team', 'date_joined')
    search_fields = ('team__name', 'member__email', 'member__first_name', 'member__last_name')
    readonly_fields = ('date_joined',)
    
    fieldsets = (
        (None, {'fields': ('team', 'member')}),
        (_('Timestamps'), {'fields': ('date_joined',)}),
    )
    
    raw_id_fields = ('team', 'member')
    
    def get_team_name(self, obj):
        """Display team name."""
        return obj.team.name
    
    get_team_name.short_description = _('Team')
    
    def get_member_name(self, obj):
        """Display member full name."""
        return obj.member.get_display_name()
    
    get_member_name.short_description = _('Member')
    
    def get_member_email(self, obj):
        """Display member email."""
        return obj.member.email
    
    get_member_email.short_description = _('Email')


class TaskCommentInline(admin.TabularInline):
    """
    Inline admin interface for TaskComment within Task admin.
    """
    model = TaskComment
    extra = 0
    readonly_fields = ('user', 'created_at', 'comment')
    fields = ('user', 'comment', 'created_at')
    can_delete = False


class TaskAttachmentInline(admin.TabularInline):
    """
    Inline admin interface for TaskAttachment within Task admin.
    """
    model = TaskAttachment
    extra = 0
    readonly_fields = ('uploaded_by', 'uploaded_at', 'file')
    fields = ('file', 'uploaded_by', 'uploaded_at')
    can_delete = False


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Admin interface for Task model.
    """
    list_display = ('title', 'get_team_name', 'assigned_to', 'status', 'priority', 'due_date', 'is_urgent')
    list_filter = ('status', 'priority', 'team', 'is_urgent', 'created_at', 'due_date')
    search_fields = ('title', 'description', 'team__name', 'assigned_to__email', 'created_by__email')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    fieldsets = (
        (_('Task Information'), {
            'fields': ('title', 'description', 'team')
        }),
        (_('Assignment'), {
            'fields': ('created_by', 'assigned_to')
        }),
        (_('Status'), {
            'fields': ('status', 'priority', 'is_urgent')
        }),
        (_('Details'), {
            'fields': ('due_date', 'tags')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    inlines = [TaskCommentInline, TaskAttachmentInline]
    raw_id_fields = ('team', 'created_by', 'assigned_to')
    date_hierarchy = 'created_at'
    
    def get_team_name(self, obj):
        """Display team name."""
        return obj.team.name
    
    get_team_name.short_description = _('Team')
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('team', 'created_by', 'assigned_to')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """
    Admin interface for TaskComment model.
    """
    list_display = ('get_task_title', 'get_user_name', 'created_at')
    list_filter = ('created_at', 'task__team')
    search_fields = ('task__title', 'user__email', 'comment')
    readonly_fields = ('created_at', 'updated_at', 'user', 'task')
    
    fieldsets = (
        (_('Comment'), {
            'fields': ('task', 'user', 'comment')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    can_delete = False
    
    def get_task_title(self, obj):
        """Display task title."""
        return obj.task.title
    
    get_task_title.short_description = _('Task')
    
    def get_user_name(self, obj):
        """Display user name."""
        return obj.user.get_display_name()
    
    get_user_name.short_description = _('User')
    
    def has_add_permission(self, request):
        """Comments can only be added via the UI."""
        return False


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    """
    Admin interface for TaskAttachment model.
    """
    list_display = ('filename', 'get_task_title', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at', 'task__team')
    search_fields = ('file', 'task__title', 'uploaded_by__email')
    readonly_fields = ('uploaded_at', 'uploaded_by', 'task')
    
    fieldsets = (
        (_('Attachment'), {
            'fields': ('task', 'file')
        }),
        (_('Upload Info'), {
            'fields': ('uploaded_by', 'uploaded_at')
        }),
    )
    
    can_delete = False
    
    def filename(self, obj):
        """Display just the filename."""
        return obj.filename
    
    filename.short_description = _('File')
    
    def get_task_title(self, obj):
        """Display task title."""
        return obj.task.title
    
    get_task_title.short_description = _('Task')
    
    def has_add_permission(self, request):
        """Attachments can only be added via the UI."""
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification model.
    """
    list_display = ('id', 'get_recipient_name', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__email', 'message')
    readonly_fields = ('created_at', 'recipient', 'task', 'notification_type', 'message')

    fieldsets = (
        (_('Notification'), {
            'fields': ('recipient', 'notification_type', 'message')
        }),
        (_('Related'), {
            'fields': ('task',)
        }),
        (_('Status'), {
            'fields': ('is_read',)
        }),
        (_('Timestamp'), {
            'fields': ('created_at',)
        }),
    )

    can_delete = False

    def get_recipient_name(self, obj):
        """Display recipient name."""
        return obj.recipient.get_display_name()

    get_recipient_name.short_description = _('Recipient')


@admin.register(TaskActivity)
class TaskActivityAdmin(admin.ModelAdmin):
    """
    Admin interface for TaskActivity model.
    """
    list_display = ('id', 'get_task_title', 'activity_type', 'get_user_name', 'created_at')
    list_filter = ('activity_type', 'created_at', 'task__team')
    search_fields = ('task__title', 'user__email', 'description')
    readonly_fields = ('created_at', 'task', 'user', 'activity_type', 'description', 'old_value', 'new_value')

    fieldsets = (
        (_('Activity'), {
            'fields': ('task', 'user', 'activity_type', 'description')
        }),
        (_('Changes'), {
            'fields': ('old_value', 'new_value')
        }),
        (_('Timestamp'), {
            'fields': ('created_at',)
        }),
    )

    can_delete = False

    def get_task_title(self, obj):
        """Display task title."""
        return obj.task.title

    get_task_title.short_description = _('Task')

    def get_user_name(self, obj):
        """Display user name."""
        return obj.user.get_display_name()

    get_user_name.short_description = _('User')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """
    Admin interface for NotificationPreference model.
    """
    list_display = ('get_user_name', 'email_notifications', 'created_at')
    list_filter = ('email_notifications', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Email Notifications'), {
            'fields': ('email_notifications',)
        }),
        (_('Notification Types'), {
            'fields': ('task_assigned', 'status_changed', 'comment_added', 'deadline_approaching', 'task_overdue')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_user_name(self, obj):
        """Display user name."""
        return obj.user.get_display_name()

    get_user_name.short_description = _('User')
