"""
Management command to backfill analytics data for existing users.

This command creates UserSignup records for all existing users who don't have one,
using their date_joined as the signup date and profile.signup_ip if available.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from myApp.models import UserSignup, Profile

User = get_user_model()


class Command(BaseCommand):
    help = 'Backfill UserSignup records for existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find users without UserSignup records
        users_without_signup = User.objects.filter(
            signup_record__isnull=True
        ).select_related('profile')
        
        total = users_without_signup.count()
        
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS('All users already have UserSignup records.')
            )
            return
        
        self.stdout.write(f'Found {total} users without UserSignup records.')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No records will be created')
            )
        
        created = 0
        skipped = 0
        
        for user in users_without_signup:
            try:
                # Get signup info from profile if available
                profile = getattr(user, 'profile', None)
                signup_ip = None
                signup_country = None
                
                if profile:
                    signup_ip = profile.signup_ip
                    signup_country = profile.signup_country
                
                if not dry_run:
                    # Create UserSignup record using date_joined as created_at
                    UserSignup.objects.create(
                        user=user,
                        ip_address=signup_ip or '',
                        user_agent='',
                        referer='',
                        created_at=user.date_joined  # Use actual signup date
                    )
                    created += 1
                    self.stdout.write(
                        f'  ✓ Created signup record for {user.username} ({user.email})'
                    )
                else:
                    self.stdout.write(
                        f'  [DRY RUN] Would create signup record for {user.username} ({user.email})'
                    )
                    created += 1
                    
            except Exception as e:
                skipped += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Error creating signup record for {user.username}: {str(e)}'
                    )
                )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Successfully created {created} UserSignup records'
                )
            )
            if skipped > 0:
                self.stdout.write(
                    self.style.WARNING(f'  Skipped {skipped} users due to errors')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n[DRY RUN] Would create {created} UserSignup records'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '\nRun without --dry-run to actually create the records.'
                )
            )

