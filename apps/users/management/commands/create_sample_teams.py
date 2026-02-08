"""
Management command to create sample teams for testing.

Usage: python manage.py create_sample_teams
"""
from django.core.management.base import BaseCommand
from apps.users.models import CustomUser, Team, TeamMembership


class Command(BaseCommand):
    help = 'Creates sample teams with members for testing'

    def handle(self, *args, **options):
        # Check if teams already exist
        if Team.objects.exists():
            self.stdout.write(self.style.WARNING('Teams already exist. Skipping creation.'))
            return

        # Get team leaders
        leader1 = CustomUser.objects.get(email='leader1@example.com')
        leader2 = CustomUser.objects.get(email='leader2@example.com')
        
        # Get team members
        members = CustomUser.objects.filter(email__startswith='member')

        # Create Team 1
        team1 = Team.objects.create(
            name='Development Team',
            description='Core development team responsible for building new features',
            leader=leader1,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS(f'Created team: {team1.name}'))

        # Add members to Team 1
        for member in members[:3]:
            TeamMembership.objects.create(team=team1, member=member)
            self.stdout.write(f'  → Added {member.get_display_name()}')

        # Create Team 2
        team2 = Team.objects.create(
            name='QA & Testing Team',
            description='Quality assurance and testing team ensuring product quality',
            leader=leader2,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS(f'Created team: {team2.name}'))

        # Add members to Team 2
        for member in members[2:]:
            TeamMembership.objects.create(team=team2, member=member)
            self.stdout.write(f'  → Added {member.get_display_name()}')

        self.stdout.write(
            self.style.SUCCESS('\n✅ Sample teams created successfully!')
        )
