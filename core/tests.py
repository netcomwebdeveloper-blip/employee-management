from datetime import date, time, timedelta
from io import BytesIO
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import EmployeeProfile, Attendance, DailyWork, LeaveRequest, MonthlyLeaveCredit


class EmployeeManagementSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Admin
        self.admin_user = User.objects.create_superuser('admin_test', 'admin@example.com', 'pass1234')
        self.admin_profile = EmployeeProfile.objects.create(
            user=self.admin_user,
            employee_code='ADM_TEST',
            role='ADMIN',
            department='Management',
            designation='Admin',
            casual_leave_balance=5
        )

        # Create HR
        self.hr_user = User.objects.create_user('hr_test', 'hr@example.com', 'pass1234')
        self.hr_profile = EmployeeProfile.objects.create(
            user=self.hr_user,
            employee_code='HR_TEST',
            role='HR',
            department='HR Dept',
            designation='HR Officer',
            casual_leave_balance=5
        )

        # Create Employee
        self.emp_user = User.objects.create_user('emp_test', 'emp@example.com', 'pass1234')
        self.emp_profile = EmployeeProfile.objects.create(
            user=self.emp_user,
            employee_code='EMP_TEST',
            role='EMPLOYEE',
            department='Engineering',
            designation='Developer',
            casual_leave_balance=3
        )

    def test_front_page_and_login_page(self):
        r_front = self.client.get('/front/')
        self.assertEqual(r_front.status_code, 200)

        r_home = self.client.get('/')
        self.assertEqual(r_home.status_code, 200)

        r_login = self.client.get('/login/')
        self.assertEqual(r_login.status_code, 200)

    def test_dashboard_redirection_by_role(self):
        # Admin redirect
        self.client.login(username='admin_test', password='pass1234')
        r = self.client.get('/dashboard/', follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('/admin-page/', r.redirect_chain[0][0])
        self.client.logout()

        # HR redirect
        self.client.login(username='hr_test', password='pass1234')
        r = self.client.get('/dashboard/', follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('/hr/', r.redirect_chain[0][0])
        self.client.logout()

        # Employee redirect
        self.client.login(username='emp_test', password='pass1234')
        r = self.client.get('/dashboard/', follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('/employee/', r.redirect_chain[0][0])
        self.client.logout()

    def test_auto_profile_creation_for_new_user(self):
        new_user = User.objects.create_user('orphan_user', 'orphan@example.com', 'pass1234')
        self.client.login(username='orphan_user', password='pass1234')
        r = self.client.get('/dashboard/', follow=True)
        self.assertEqual(r.status_code, 200)
        profile = EmployeeProfile.objects.filter(user=new_user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.role, 'EMPLOYEE')

    def test_employee_punch_in_and_out(self):
        self.client.login(username='emp_test', password='pass1234')

        # Punch in
        r = self.client.post('/employee/', {'action': 'punch_in'})
        self.assertEqual(r.status_code, 302)
        att = Attendance.objects.filter(employee=self.emp_profile, date=date.today()).first()
        self.assertIsNotNone(att)
        self.assertIsNotNone(att.in_time)

        # Punch out
        r = self.client.post('/employee/', {'action': 'punch_out'})
        self.assertEqual(r.status_code, 302)
        att.refresh_from_db()
        self.assertIsNotNone(att.out_time)
        self.assertNotEqual(att.total_work_time, "-")

    def test_employee_daily_work_submission(self):
        self.client.login(username='emp_test', password='pass1234')
        r = self.client.post('/employee/', {
            'action': 'daily_work',
            'project_name': 'ERP Module',
            'work_details': 'Implemented report generation',
            'status': 'In Progress'
        })
        self.assertEqual(r.status_code, 302)
        work = DailyWork.objects.filter(employee=self.emp_profile, project_name='ERP Module').first()
        self.assertIsNotNone(work)
        self.assertEqual(work.status, 'In Progress')

    def test_employee_leave_request_and_approval(self):
        self.client.login(username='emp_test', password='pass1234')
        today = date.today()

        # Submit leave
        r = self.client.post('/employee/', {
            'action': 'leave_request',
            'leave_type': 'Casual Leave',
            'from_date': today.strftime('%Y-%m-%d'),
            'to_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
            'reason': 'Family event'
        })
        self.assertEqual(r.status_code, 302)
        leave = LeaveRequest.objects.filter(employee=self.emp_profile, reason='Family event').first()
        self.assertIsNotNone(leave)
        self.assertEqual(leave.total_days, 2)
        self.assertEqual(leave.status, 'Pending')
        self.client.logout()

        # HR approves leave
        self.emp_profile.refresh_from_db()
        balance_before = self.emp_profile.casual_leave_balance
        self.client.login(username='hr_test', password='pass1234')
        r = self.client.get(f'/leave/{leave.id}/Approved/')
        self.assertEqual(r.status_code, 302)
        leave.refresh_from_db()
        self.emp_profile.refresh_from_db()
        self.assertEqual(leave.status, 'Approved')
        self.assertEqual(self.emp_profile.casual_leave_balance, balance_before - 2)

    def test_punch_machine_csv_upload(self):
        self.client.login(username='hr_test', password='pass1234')
        csv_data = (
            "employee_code,date,time,type\n"
            "EMP_TEST,2026-10-01,09:00:00,in\n"
            "EMP_TEST,2026-10-01,18:00:00,out\n"
        ).encode('utf-8')
        csv_file = SimpleUploadedFile('test_punch.csv', csv_data, content_type='text/csv')

        r = self.client.post('/hr/', {'action': 'punch_machine_upload', 'csv_file': csv_file})
        self.assertEqual(r.status_code, 302)

        att = Attendance.objects.filter(employee=self.emp_profile, date=date(2026, 10, 1)).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.in_time, time(9, 0))
        self.assertEqual(att.out_time, time(18, 0))
        self.assertEqual(att.update_source, 'Punch Machine CSV')

    def test_admin_create_and_delete_user(self):
        self.client.login(username='admin_test', password='pass1234')

        # Create user
        r = self.client.post('/admin-page/', {
            'username': 'created_emp',
            'password': 'testpassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'created@example.com',
            'employee_code': 'CREATED001',
            'role': 'EMPLOYEE',
            'department': 'Testing',
            'designation': 'QA',
            'casual_leave_balance': 2
        })
        self.assertEqual(r.status_code, 302)
        created_profile = EmployeeProfile.objects.filter(employee_code='CREATED001').first()
        self.assertIsNotNone(created_profile)

        # Delete user
        r_del = self.client.get(f'/delete-employee/{created_profile.id}/')
        self.assertEqual(r_del.status_code, 302)
        self.assertFalse(EmployeeProfile.objects.filter(employee_code='CREATED001').exists())
        self.assertFalse(User.objects.filter(username='created_emp').exists())
