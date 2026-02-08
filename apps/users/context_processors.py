"""
Custom context processors for the users app.
"""
from .models import Notification


def notifications(request):
    """
    Provide recent notifications and unread count for the navbar dropdown.
    """
    if not request.user.is_authenticated:
        return {}

    notifications_qs = Notification.objects.filter(recipient=request.user).select_related('task')
    unread = notifications_qs.filter(is_read=False)

    return {
        'navbar_unread_notification_count': unread.count(),
        'navbar_recent_notifications': notifications_qs[:10],
    }

