from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import EmployeeProfile


class Command(BaseCommand):
    help = 'Create demo Admin, HR, and Employee users'

    def create_user_with_profile(self, username, password, first_name, last_name, email, code, role, department, designation, phone):
        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email

        if role == 'ADMIN':
            user.is_staff = True
            user.is_superuser = True
        user.save()

        EmployeeProfile.objects.get_or_create(
            user=user,
            defaults={
                'employee_code': code,
                'role': role,
                'department': department,
                'designation': designation,
                'phone': phone,
                'address': 'Tamil Nadu',
                'casual_leave_balance': 0,
            }
        )

    def handle(self, *args, **kwargs):
        self.create_user_with_profile('admin', 'admin12345', 'System', 'Admin', 'admin@example.com', 'ADM001', 'ADMIN', 'Management', 'System Admin', '9876543200')
        self.create_user_with_profile('hr', 'hr12345', 'HR', 'Manager', 'hr@example.com', 'HR001', 'HR', 'Human Resource', 'HR Manager', '9876543210')
        self.create_user_with_profile('emp', 'emp12345', 'Mathan', 'M', 'emp@example.com', 'EMP001', 'EMPLOYEE', 'IT', 'Frontend Developer', '9876543211')

        self.stdout.write(self.style.SUCCESS('Demo users created successfully.'))
        self.stdout.write('Admin Login: username=admin password=admin12345')
        self.stdout.write('HR Login: username=hr password=hr12345')
        self.stdout.write('Employee Login: username=emp password=emp12345')
