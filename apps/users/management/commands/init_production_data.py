import os
from pathlib import Path
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.employees.models import Employee


class Command(BaseCommand):
    help = 'Seeds initial production data (departments, employees, attendance, payroll) and guarantees default credentials.'

    def handle(self, *args, **options):
        fixture_path = Path(__file__).resolve().parent.parent.parent.parent / 'database' / 'seed_data.json'

        # 1. Load seed fixture if database is missing employees
        if Employee.objects.count() == 0 and fixture_path.exists():
            self.stdout.write(f"Seeding database from fixture: {fixture_path}")
            try:
                call_command('loaddata', str(fixture_path), verbosity=1)
                self.stdout.write(self.style.SUCCESS("Database seeded successfully."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error loading fixture: {e}"))

        # 2. Explicitly ensure default login accounts and passwords
        creds = [
            ('NETCOM', 'Netcom@2026@Netcom', True, True, 'NETCOM', 'Administrator', 'admin@netcom.com'),
            ('hr', 'hr12345', False, False, 'HR', 'Manager', 'hr@netcom.com'),
            ('emp', 'emp12345', False, False, 'Regular', 'Employee', 'emp@netcom.com'),
            ('08092003', 'emp12345', False, False, 'Mathan', 'M', 'mathan003m@gmail.com'),
        ]

        for username, password, is_super, is_staff, first, last, email in creds:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'is_superuser': is_super,
                    'is_staff': is_staff,
                    'first_name': first,
                    'last_name': last,
                    'email': email,
                }
            )
            user.set_password(password)
            user.is_superuser = is_super
            user.is_staff = is_staff
            user.is_active = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"User '{username}' verified and password configured."))
