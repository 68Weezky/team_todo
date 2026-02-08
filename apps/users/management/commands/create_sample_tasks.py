from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.users.models import Team, Task, TaskComment, CustomUser, TeamMembership


class Command(BaseCommand):
    help = 'Create sample tasks for testing task management features'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample tasks...'))
        
        # Get or create sample users
        try:
            admin_user = CustomUser.objects.get(role='admin')
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.WARNING('No admin user found. Skipping...'))
            return

        # Get active teams
        teams = Team.objects.filter(is_active=True)[:3]
        
        if not teams.exists():
            self.stdout.write(self.style.WARNING('No active teams found. Skipping...'))
            return

        # Sample task data
        sample_tasks = [
            {
                'title': 'Design Homepage Mockup',
                'description': 'Create a modern, responsive homepage mockup in Figma. Include mobile, tablet, and desktop views.',
                'priority': 'high',
                'status': 'in_progress',
                'due_days': 3,
                'is_urgent': True,
            },
            {
                'title': 'API Documentation',
                'description': 'Document all REST API endpoints including request/response examples and error handling.',
                'priority': 'medium',
                'status': 'not_started',
                'due_days': 7,
                'is_urgent': False,
            },
            {
                'title': 'Database Schema Optimization',
                'description': 'Review and optimize database queries. Add indexes where needed and refactor slow queries.',
                'priority': 'high',
                'status': 'in_progress',
                'due_days': 5,
                'is_urgent': False,
            },
            {
                'title': 'User Testing Session',
                'description': 'Conduct user testing with 5 beta users. Document feedback and create improvement list.',
                'priority': 'critical',
                'status': 'not_started',
                'due_days': 2,
                'is_urgent': True,
            },
            {
                'title': 'Fix Login Bug',
                'description': 'Fix the occasional 404 error on login page. Issue appears intermittently on mobile devices.',
                'priority': 'critical',
                'status': 'in_progress',
                'due_days': 1,
                'is_urgent': True,
            },
            {
                'title': 'Write Unit Tests',
                'description': 'Write comprehensive unit tests for user authentication module. Target 80%+ code coverage.',
                'priority': 'medium',
                'status': 'not_started',
                'due_days': 10,
                'is_urgent': False,
            },
            {
                'title': 'Create Admin Dashboard',
                'description': 'Build admin dashboard with analytics, user stats, and system health monitoring.',
                'priority': 'medium',
                'status': 'review',
                'due_days': 4,
                'is_urgent': False,
            },
            {
                'title': 'Security Audit',
                'description': 'Perform comprehensive security audit including XSS, CSRF, and SQL injection testing.',
                'priority': 'critical',
                'status': 'not_started',
                'due_days': 6,
                'is_urgent': True,
            },
        ]

        created_count = 0
        
        for team in teams:
            # Get team members (including leader)
            team_members_list = list(team.members.values_list('member', flat=True))
            team_members_list.append(team.leader.id)  # Include leader
            
            if not team_members_list:
                self.stdout.write(self.style.WARNING(f'No members in team "{team.name}". Skipping...'))
                continue
            
            assignees = list(CustomUser.objects.filter(id__in=team_members_list)[:5])
            
            if not assignees:
                continue
            
            # Create 2-3 tasks per team
            for i, task_data in enumerate(sample_tasks[:3]):
                if i >= len(assignees):
                    assigned_to = assignees[i % len(assignees)]
                else:
                    assigned_to = assignees[i]
                
                due_date = timezone.now() + timedelta(days=task_data['due_days'])
                
                task, created = Task.objects.get_or_create(
                    title=f"{task_data['title']} - {team.name}",
                    team=team,
                    defaults={
                        'description': task_data['description'],
                        'created_by': admin_user,
                        'assigned_to': assigned_to,
                        'priority': task_data['priority'],
                        'status': task_data['status'],
                        'due_date': due_date,
                        'is_urgent': task_data['is_urgent'],
                        'tags': 'sample,testing',
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Created: {task.title}')
                    )
                    
                    # Add sample comment
                    if task_data['status'] in ['in_progress', 'review']:
                        TaskComment.objects.get_or_create(
                            task=task,
                            user=assigned_to,
                            defaults={
                                'comment': 'Started working on this task. Making good progress!',
                            }
                        )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Successfully created {created_count} sample tasks!')
        )
