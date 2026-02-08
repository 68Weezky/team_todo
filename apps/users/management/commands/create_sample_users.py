"""
Management command to create sample users for testing.

Usage: python manage.py create_sample_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates sample users with different roles for testing'

    def handle(self, *args, **options):
        # Check if users already exist
        if User.objects.exists():
            self.stdout.write(self.style.WARNING('Users already exist. Skipping creation.'))
            return

        # Create admin user
        admin_user = User.objects.create_superuser(
            username='admin@example.com',
            email='admin@example.com',
            password='admin123456',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        self.stdout.write(
            self.style.SUCCESS(f'Created admin user: {admin_user.email}')
        )

        # Create team leader users
        for i in range(2):
            leader = User.objects.create_user(
                username=f'leader{i+1}@example.com',
                email=f'leader{i+1}@example.com',
                password='leader123456',
                first_name=f'Leader',
                last_name=f'User {i+1}',
                role='team_leader'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created team leader: {leader.email}')
            )

        # Create team member users
        for i in range(5):
            member = User.objects.create_user(
                username=f'member{i+1}@example.com',
                email=f'member{i+1}@example.com',
                password='member123456',
                first_name=f'Team',
                last_name=f'Member {i+1}',
                role='team_member'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created team member: {member.email}')
            )

        self.stdout.write(
            self.style.SUCCESS('\n✅ Sample users created successfully!')
        )
        self.stdout.write(self.style.WARNING('\nCredentials for testing:'))
        self.stdout.write('  Admin: admin@example.com / admin123456')
        self.stdout.write('  Leader: leader1@example.com / leader123456')
        self.stdout.write('  Member: member1@example.com / member123456')
