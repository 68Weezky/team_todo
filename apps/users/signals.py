"""
Signals for the users app.

Auto-create notification preferences when user is created.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, NotificationPreference


@receiver(post_save, sender=CustomUser)
def create_notification_preference(sender, instance, created, **kwargs):
    """
    Create NotificationPreference instance when CustomUser is created.
    """
    if created:
        NotificationPreference.objects.get_or_create(user=instance)


@receiver(post_save, sender=CustomUser)
def save_notification_preference(sender, instance, **kwargs):
    """
    Save NotificationPreference instance when CustomUser is saved.
    """
    if hasattr(instance, 'notification_preferences'):
        instance.notification_preferences.save()
