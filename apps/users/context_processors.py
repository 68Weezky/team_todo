"""
Custom context processors for the users app.
"""


def notifications(request):
    """
    Provide recent notifications and unread count for the navbar dropdown.
    Fails safe so a missing table or DB error never causes a 500.
    """
    if not request.user.is_authenticated:
        return {
            'navbar_unread_notification_count': 0,
            'navbar_recent_notifications': [],
        }
    try:
        from .models import Notification
        notifications_qs = Notification.objects.filter(recipient=request.user).select_related('task')
        unread = notifications_qs.filter(is_read=False)
        return {
            'navbar_unread_notification_count': unread.count(),
            'navbar_recent_notifications': list(notifications_qs[:10]),
        }
    except Exception:
        return {
            'navbar_unread_notification_count': 0,
            'navbar_recent_notifications': [],
        }

