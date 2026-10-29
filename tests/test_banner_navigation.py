from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.employees.models import Employee
from apps.departments.models import Department, Designation

User = get_user_model()

class BannerAndNavigationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="Software Engineering")
        self.desig = Designation.objects.create(title="Full Stack Developer", department=self.dept)
        self.user = User.objects.create_user(
            username="emp_tester",
            email="tester@example.com",
            first_name="Tester",
            last_name="Staff",
            password="testpassword123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            employee_code="EMP-TEST-99",
            department=self.dept,
            designation=self.desig,
            role="EMPLOYEE",
            casual_leave_balance=1
        )
        self.client.login(username="emp_tester", password="testpassword123")

    def test_top_navigation_bar_rendered_for_logged_in_employee(self):
        """Top navigation bar must render the 4 required pills: Employee Dashboard, HR Support, Leave Management, Profile."""
        resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        self.assertIn('class="employee-top-nav-bar"', html)
        self.assertIn('Employee Dashboard', html)
        self.assertIn('HR Support', html)
        self.assertIn('Leave Management', html)
        self.assertIn('Profile', html)

    def test_employee_dashboard_banner_dynamic_details(self):
        """Employee Dashboard banner must display dynamic name, Staff ID, Role, glow badge, and background."""
        resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        self.assertIn('employee_dashboard_bg.png', html)
        self.assertIn('EMP-TEST-99', html)
        self.assertIn('Full Stack Developer', html)
        self.assertIn('Tester!', html)
        self.assertIn('Great to see you again! Keep up the good work!', html)

    def test_daily_works_banner_style_and_details(self):
        """Daily works banner must follow the same style with employee details, avatar, and daily_works_bg.png."""
        resp = self.client.get(reverse('attendance:daily_work'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        self.assertIn('daily_works_bg.png', html)
        self.assertIn('EMP-TEST-99', html)
        self.assertIn('Full Stack Developer', html)
        self.assertIn('Daily Work Planning &amp; Tasks', html)
        self.assertIn('Plan, track, and log your daily milestones', html)

    def test_profile_banner_style_and_details(self):
        """Profile page banner must follow the same style with employee details, my_profile_bg.png, and ACCOUNT SETTINGS."""
        resp = self.client.get(reverse('users:profile'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        self.assertIn('my_profile_bg.png', html)
        self.assertIn('EMP-TEST-99', html)
        self.assertIn('Full Stack Developer', html)
        self.assertIn('ACCOUNT SETTINGS', html)
        self.assertIn('Manage your personal information', html)

    def test_leave_management_banner_style(self):
        """Leave list banner must display leave_management_bg.png and casual leave balance card."""
        resp = self.client.get(reverse('leave_management:list'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        self.assertIn('leave_management_bg.png', html)
        self.assertIn('CASUAL LEAVE BALANCE', html)
        self.assertIn('1 Days', html)
        self.assertIn('Remaining Permission', html)

    def test_hr_support_banner_style(self):
        """HR Support banner must display hr_support_bg.png and HR Support header."""
        resp = self.client.get(reverse('dashboard:hr_support'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        self.assertIn('hr_support_bg.png', html)
        self.assertIn('HR Support', html)
