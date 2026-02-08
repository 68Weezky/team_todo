"""
Views for in-app notification listing and mark-as-read actions.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


@login_required
def notification_list(request):
    """
    Display notifications for the current user.
    """
    notifications_qs = Notification.objects.filter(
        recipient=request.user
    ).select_related('task')

    paginator = Paginator(notifications_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def mark_notification_read(request, pk):
    """
    Mark a single notification as read and optionally redirect to related task.
    """
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])

    task = notification.task
    if task:
        return redirect('users:task_detail', team_id=task.team_id, task_id=task.id)

    messages.info(request, 'Notification marked as read.')
    return redirect('users:notification_list')


@login_required
def mark_all_notifications_read(request):
    """
    Mark all notifications for the current user as read.
    """
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('users:notification_list')

