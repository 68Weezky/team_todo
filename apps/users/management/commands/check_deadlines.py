from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import Task
from apps.users.task_views import create_notification


class Command(BaseCommand):
    help = "Check for tasks with approaching or overdue deadlines and notify users."

    def handle(self, *args, **options):
        now = timezone.now()
        in_24_hours = now + timedelta(hours=24)

        self.stdout.write("Checking task deadlines...")

        # Tasks due in next 24 hours
        upcoming_tasks = Task.objects.filter(
            due_date__gte=now,
            due_date__lte=in_24_hours,
            status__in=['not_started', 'in_progress', 'review'],
            assigned_to__isnull=False,
        ).select_related('assigned_to', 'team')

        for task in upcoming_tasks:
            create_notification(
                recipient=task.assigned_to,
                notification_type='deadline_approaching',
                message=(
                    f'Task "{task.title}" in team "{task.team.name}" is due within 24 hours.'
                ),
                task=task,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Notified {task.assigned_to.email} about approaching deadline for task {task.id}.'
                )
            )

        # Overdue tasks
        overdue_tasks = Task.objects.filter(
            due_date__lt=now,
            status__in=['not_started', 'in_progress', 'review'],
            assigned_to__isnull=False,
        ).select_related('assigned_to', 'team')

        for task in overdue_tasks:
            create_notification(
                recipient=task.assigned_to,
                notification_type='task_overdue',
                message=(
                    f'Task "{task.title}" in team "{task.team.name}" is overdue.'
                ),
                task=task,
            )
            self.stdout.write(
                self.style.WARNING(
                    f'Notified {task.assigned_to.email} about overdue task {task.id}.'
                )
            )

        self.stdout.write(self.style.SUCCESS("Deadline check completed."))

