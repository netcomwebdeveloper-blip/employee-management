from datetime import date, time, timedelta, datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth.models import User
from apps.departments.models import Department, Designation
from apps.employees.models import Employee
from apps.attendance.models import Attendance, AttendanceAuditLog
from apps.attendance.services import reset_daily_missed_punch_in_status, mark_employee_official_duty
from apps.leave_management.models import LeaveRequest, HRNotification
from apps.payroll.models import SalaryStructure, PayrollRecord
from apps.payroll.views import calculate_payroll_for_employee
from unittest.mock import patch


class AttendanceAndMessagingTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Department & Designation
        self.dept = Department.objects.create(name='Operations', code='OPS')
        self.desig = Designation.objects.create(department=self.dept, title='Specialist')

        # Admin user
        self.admin_user = User.objects.create_superuser('NETCOM', 'admin@netcom.com', 'Netcom@2026@Netcom')
        self.admin_profile = Employee.objects.create(
            user=self.admin_user,
            employee_code='NETCOM001',
            role='ADMIN',
            department=self.dept,
            designation=self.desig,
            casual_leave_balance=10
        )

        # HR user
        self.hr_user = User.objects.create_user('hr_user', 'hr@example.com', 'hr12345')
        self.hr_profile = Employee.objects.create(
            user=self.hr_user,
            employee_code='HR001',
            role='HR',
            department=self.dept,
            designation=self.desig,
            casual_leave_balance=10
        )

        # Employee user
        self.emp_user = User.objects.create_user('emp_john', 'john@example.com', 'john12345')
        self.emp_profile = Employee.objects.create(
            user=self.emp_user,
            employee_code='EMP101',
            role='EMPLOYEE',
            department=self.dept,
            designation=self.desig,
            basic_salary=Decimal('30000.00'),
            casual_leave_balance=1
        )

        today = timezone.localdate()
        from apps.leave_management.models import MonthlyLeaveCredit
        MonthlyLeaveCredit.objects.get_or_create(
            employee=self.emp_profile,
            year=today.year,
            month=today.month,
            defaults={'casual_added': 1}
        )

        # Salary Structure for payroll
        SalaryStructure.objects.create(
            employee=self.emp_profile,
            basic_salary=Decimal('30000.00'),
            hra=Decimal('5000.00'),
            allowances=Decimal('5000.00'),
            pf_deduction=Decimal('1800.00'),
            tax_deduction=Decimal('200.00')
        )

    def test_mandatory_punch_in_and_midnight_reset(self):
        today = timezone.localdate()
        past_date = today - timedelta(days=2)

        # Create historical attendance record (must NEVER be altered or deleted)
        past_att = Attendance.objects.create(
            employee=self.emp_profile,
            date=past_date,
            status='Present',
            in_time=time(9, 30),
            out_time=time(18, 30)
        )

        # Unpunched yesterday record
        yesterday = today - timedelta(days=1)
        yesterday_att = Attendance.objects.create(
            employee=self.emp_profile,
            date=yesterday,
            status='Pending Punch-In'
        )

        # For today: unpunched employee remains Pending Punch-In during the active calendar day
        reset_daily_missed_punch_in_status(target_date=today)
        today_att = Attendance.objects.get(employee=self.emp_profile, date=today)
        self.assertEqual(today_att.status, 'Pending Punch-In')
        self.assertNotEqual(today_att.status, 'Missed Punch-In')

        # Midnight auto-evaluation: past unpunched day evaluated at 12:00 AM midnight
        yesterday_att.refresh_from_db()
        self.assertEqual(yesterday_att.status, 'Missed Punch-In')
        self.assertEqual(yesterday_att.update_source, 'Midnight Daily Auto-Reset')

        # Verify historical records were NOT altered or deleted
        past_att_refreshed = Attendance.objects.get(id=past_att.id)
        self.assertEqual(past_att_refreshed.status, 'Present')
        self.assertEqual(past_att_refreshed.date, past_date)

    def test_missing_punch_out_handling_and_payroll_exclusion(self):
        today = timezone.localdate()

        # Employee punches in at 09:15 but misses punch-out
        att = Attendance.objects.create(
            employee=self.emp_profile,
            date=today,
            in_time=time(9, 15)
        )

        # Verify status and calculations
        self.assertEqual(att.status, 'Missing Punch-Out')
        self.assertTrue(att.is_missing_punch_out)
        self.assertEqual(att.total_work_minutes, 0)
        self.assertIn('Incomplete', att.total_work_time)
        self.assertFalse(att.is_full_day)
        self.assertFalse(att.is_half_day)

        # Verify payroll excludes missing punch-out day and does not finalize salary on incomplete data
        payroll_data = calculate_payroll_for_employee(self.emp_profile, today.year, today.month)
        self.assertEqual(payroll_data['full_days'], 0)
        self.assertEqual(payroll_data['half_days'], 0)
        self.assertIn('missing punch-out', payroll_data['remarks'])

        # Verify employee dashboard has removed the unwanted missing punch-out alert banners per user request
        self.client.login(username='emp_john', password='john12345')
        response = self.client.get('/dashboard/employee/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Incomplete Attendance Detected — Missing Punch-Out')
        self.client.logout()

    def test_official_duty_marking_and_payroll(self):
        target_date = date(2026, 9, 15)

        # First give employee a leave on that date that reduced balance
        initial_balance = self.emp_profile.casual_leave_balance  # 1
        LeaveRequest.objects.create(
            employee=self.emp_profile,
            leave_type='Casual Leave',
            from_date=target_date,
            to_date=target_date,
            status='Approved',
            total_days=1
        )
        self.emp_profile.casual_leave_balance = 0
        self.emp_profile.save()
        self.assertEqual(self.emp_profile.casual_leave_balance, 0)

        # HR marks employee as on Official Office Duty
        self.client.login(username='hr_user', password='hr12345')
        response = self.client.post('/dashboard/', {
            'action': 'mark_official_duty',
            'employee_id': self.emp_profile.id,
            'date': target_date.strftime('%Y-%m-%d'),
            'duty_title': 'Client Site Technical Audit',
            'notes': 'Official deployment at client premise'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # Check attendance record (marked as Present instead of Leave, with official duty properties)
        att = Attendance.objects.get(employee=self.emp_profile, date=target_date)
        self.assertEqual(att.status, 'Present')
        self.assertTrue(att.is_official_duty)
        self.assertTrue(att.is_full_day)
        self.assertEqual(att.total_work_minutes, 540)  # 9 hours credited

        # Check leave restoration
        self.emp_profile.refresh_from_db()
        self.assertEqual(self.emp_profile.casual_leave_balance, initial_balance)  # Restored to 1

        # Check payroll credits full day Present with zero deduction for that month
        payroll_data = calculate_payroll_for_employee(self.emp_profile, 2026, 9)
        self.assertEqual(payroll_data['full_days'], 1)
        self.assertEqual(payroll_data['absent_days'], 0)
        self.assertEqual(payroll_data['incomplete_punch_days'], [])

    def test_unauthorized_official_duty_rejected(self):
        target_date = timezone.localdate()
        # Non-HR/Admin employee attempts to mark official duty
        self.client.login(username='emp_john', password='john12345')
        response = self.client.post('/attendance/mark-official-duty/', {
            'employee_id': self.emp_profile.id,
            'date': target_date.strftime('%Y-%m-%d'),
            'duty_title': 'Self assigned'
        }, follow=True)
        # Should be forbidden or redirected
        att = Attendance.objects.filter(employee=self.emp_profile, date=target_date, status='Official Duty').first()
        self.assertIsNone(att)
        self.client.logout()

    def test_send_message_feature_between_employee_and_hr(self):
        # 1. Employee sends enquiry message to HR
        self.client.login(username='emp_john', password='john12345')
        response = self.client.post('/dashboard/employee/', {
            'action': 'send_hr_message',
            'category': 'Attendance Regularization / Missing Punch-Out',
            'subject': 'Missing Punch-Out Correction',
            'message': 'Dear HR, I missed my punch out yesterday due to emergency client visit. Kindly update my out time to 18:30.'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your message has been sent directly to the HR department.')
        self.client.logout()

        # Verify message created as HRNotification
        notif = HRNotification.objects.filter(recipient_role='HR', title__contains='Missing Punch-Out Correction').first()
        self.assertIsNotNone(notif)
        self.assertIn('Missing Punch-Out Correction', notif.title)
        self.assertIn('18:30', notif.message)
        self.assertFalse(notif.is_read)

        # 2. HR views message on HR Dashboard
        self.client.login(username='hr_user', password='hr12345')
        hr_response = self.client.get('/dashboard/hr/')
        self.assertEqual(hr_response.status_code, 200)
        self.assertContains(hr_response, 'Missing Punch-Out Correction')
        self.assertContains(hr_response, 'Dear HR, I missed my punch out yesterday')

        # 3. HR toggles message as read / reviewed
        toggle_response = self.client.post('/dashboard/', {
            'action': 'toggle_notification_read',
            'notification_id': notif.id
        }, follow=True)
        self.assertEqual(toggle_response.status_code, 200)

        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.client.logout()

    def test_punch_fails_when_gps_or_selfie_missing(self):
        self.client.login(username='emp_john', password='john12345')
        fake_photo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        # 1. Missing GPS
        r1 = self.client.post('/attendance/punch/', {'action': 'punch_in', 'photo_data': fake_photo}, follow=True)
        messages1 = [str(m) for m in r1.context['messages']]
        self.assertTrue(any("GPS location and a live selfie are mandatory" in m for m in messages1))

        # 2. Missing Selfie
        r2 = self.client.post('/attendance/punch/', {'action': 'punch_in', 'latitude': '12.9716', 'longitude': '77.5946'}, follow=True)
        messages2 = [str(m) for m in r2.context['messages']]
        self.assertTrue(any("GPS location and a live selfie are mandatory" in m for m in messages2))

        # 3. Both present -> Success
        r3 = self.client.post('/attendance/punch/', {
            'action': 'punch_in',
            'photo_data': fake_photo,
            'latitude': '12.9716',
            'longitude': '77.5946'
        }, follow=True)
        messages3 = [str(m) for m in r3.context['messages']]
        self.assertTrue(any("Punch In recorded" in m for m in messages3))
        self.client.logout()

    def test_hr_manual_punch_out_correction_and_audit_trail(self):
        target_date = date(2026, 9, 20)
        # Employee has punch-in but missed punch-out
        att = Attendance.objects.create(
            employee=self.emp_profile,
            date=target_date,
            in_time=time(9, 0)
        )
        self.assertEqual(att.status, 'Missing Punch-Out')

        # 1. Employee cannot correct attendance (unauthorized)
        self.client.login(username='emp_john', password='john12345')
        r_unauth = self.client.post('/attendance/correct-punch-out/', {
            'employee_id': self.emp_profile.id,
            'date': target_date.strftime('%Y-%m-%d'),
            'out_time': '18:15',
            'reason': 'Self regularization'
        })
        self.assertEqual(r_unauth.status_code, 302)
        self.client.logout()

        # 2. HR corrects punch out
        self.client.login(username='hr_user', password='hr12345')
        r_hr = self.client.post('/attendance/correct-punch-out/', {
            'employee_id': self.emp_profile.id,
            'date': target_date.strftime('%Y-%m-%d'),
            'out_time': '18:15',
            'reason': 'Employee forgot punch-out; verified via gate security log'
        }, follow=True)
        self.assertEqual(r_hr.status_code, 200)
        self.client.logout()

        # Verify attendance record updated
        att.refresh_from_db()
        self.assertEqual(att.out_time, time(18, 15))
        self.assertEqual(att.status, 'Present')
        self.assertEqual(att.total_work_minutes, 555)  # 9h 15m >= 9h -> full day
        self.assertTrue(att.is_full_day)

        # Verify audit log created
        log = AttendanceAuditLog.objects.filter(attendance=att, action='HR_MANUAL_PUNCH_OUT_CORRECTION').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changed_by, self.hr_user)
        self.assertIn('gate security log', log.new_values)
        self.assertIn('18:15', log.new_values)

    def test_salary_calculation_tiers_and_permissions(self):
        # 1. >= 9 hours -> Full day salary credit (0 deduction)
        d1 = date(2026, 8, 1)
        Attendance.objects.create(
            employee=self.emp_profile,
            date=d1,
            in_time=time(9, 0),
            out_time=time(18, 0)  # exactly 9 hours (540 mins)
        )

        # 2. >= 4.5 hours and < 9 hours -> Half day salary credit (0.5 deduction)
        d2 = date(2026, 8, 2)
        Attendance.objects.create(
            employee=self.emp_profile,
            date=d2,
            in_time=time(9, 0),
            out_time=time(14, 0)  # 5 hours (300 mins)
        )

        # 3. Approved permission <= 2 hours -> Full salary credit (0 deduction)
        d3 = date(2026, 8, 3)
        Attendance.objects.create(
            employee=self.emp_profile,
            date=d3,
            in_time=time(9, 0),
            out_time=time(16, 30),  # 7.5 hours
            is_permission=True,
            permission_hours=Decimal('2.00')
        )

        payroll_data = calculate_payroll_for_employee(self.emp_profile, 2026, 8)
        self.assertEqual(payroll_data['full_days'], 1)  # d1 (9h)
        self.assertEqual(payroll_data['half_days'], 1)  # d2 (5h)
        self.assertEqual(payroll_data['permission_days'], 1)  # d3 (7.5h + 2h permission -> 0 deduction)

    def test_office_leave_calendar_green_status_and_midnight_reset(self):
        from apps.attendance.services import mark_office_holiday_calendar, reset_daily_missed_punch_in_status
        from apps.leave_management.models import OfficePaidLeave
        target_date = date(2026, 11, 10)

        # Mark office holiday via calendar service
        holiday = mark_office_holiday_calendar(
            target_date=target_date,
            title='National Innovation Day',
            description='Approved office-wide celebration',
            marked_by=self.hr_user
        )
        self.assertIsNotNone(holiday)

        # Verify all employees have attendance marked On Leave / Paid Leave for the Office
        att = Attendance.objects.get(employee=self.emp_profile, date=target_date)
        self.assertEqual(att.status, 'On Leave')
        self.assertEqual(att.leave_type, 'Paid Leave for the Office')

        # Verify payroll gives full credit (0 deduction, not LWP)
        payroll_data = calculate_payroll_for_employee(self.emp_profile, 2026, 11)
        self.assertEqual(payroll_data['approved_leaves'], 1)
        self.assertEqual(payroll_data['absent_days'], 0)

        # Midnight reset preserves past records
        count = reset_daily_missed_punch_in_status(target_date=date(2026, 11, 11))
        att.refresh_from_db()
        self.assertEqual(att.status, 'On Leave')
        self.assertEqual(att.leave_type, 'Paid Leave for the Office')

    def test_employee_password_update_reflects_in_raw_password(self):
        self.client.login(username='emp_john', password='john12345')
        resp = self.client.post('/users/profile/', {
            'change_password': '1',
            'old_password': 'john12345',
            'new_password1': 'newSecret99!',
            'new_password2': 'newSecret99!'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.emp_profile.refresh_from_db()
        self.assertEqual(self.emp_profile.raw_password, 'newSecret99!')

        # Verify HR dashboard shows the updated password
        self.client.logout()
        self.client.login(username='hr_user', password='hr12345')
        resp_hr = self.client.get('/dashboard/hr/')
        self.assertEqual(resp_hr.status_code, 200)
        self.assertContains(resp_hr, 'newSecret99!')

    def test_permission_request_workflow_validation_and_hr_approval(self):
        target_date = date(2026, 10, 20)
        self.client.login(username='emp_john', password='john12345')

        # 1. Valid permission request (90 mins <= 120 mins)
        resp = self.client.post('/leave/', {
            'leave_type': 'Permission (Up to 2 Hours)',
            'permission_date': target_date.strftime('%Y-%m-%d'),
            'from_time': '10:00',
            'to_time': '11:30',
            'reason': 'Medical consultation'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        perm = LeaveRequest.objects.filter(employee=self.emp_profile, from_date=target_date, leave_type='Permission (Up to 2 Hours)').first()
        self.assertIsNotNone(perm)
        self.assertEqual(perm.status, 'Pending')
        self.assertIn('Medical consultation', perm.reason)
        self.assertIn('1h 30m', perm.approval_type)

        # 2. Permission duration exceeding remaining monthly balance (> remaining quota) must be rejected
        other_date = date(2026, 10, 21)
        resp_invalid = self.client.post('/leave/', {
            'leave_type': 'Permission (Up to 2 Hours)',
            'permission_date': other_date.strftime('%Y-%m-%d'),
            'from_time': '09:00',
            'to_time': '16:00',  # 7 hours exceeds 5.0h monthly balance
            'reason': 'Personal errand'
        }, follow=True)
        self.assertEqual(resp_invalid.status_code, 200)
        self.assertFalse(LeaveRequest.objects.filter(employee=self.emp_profile, from_date=other_date).exists())

        # 3. Duplicate request on the same date must be rejected
        resp_dup = self.client.post('/leave/', {
            'leave_type': 'Permission (Up to 2 Hours)',
            'permission_date': target_date.strftime('%Y-%m-%d'),
            'from_time': '14:00',
            'to_time': '15:00',
            'reason': 'Another appointment'
        }, follow=True)
        self.assertEqual(resp_dup.status_code, 200)
        self.assertEqual(LeaveRequest.objects.filter(employee=self.emp_profile, from_date=target_date).count(), 1)
        self.client.logout()

        # 4. HR approves permission
        self.client.login(username='hr_user', password='hr12345')
        resp_approve = self.client.post(f'/leave/{perm.id}/review/', {
            'status': 'Approved',
            'classification': 'Approved Permission'
        }, follow=True)
        self.assertEqual(resp_approve.status_code, 200)

        perm.refresh_from_db()
        self.assertEqual(perm.status, 'Approved')

        att = Attendance.objects.get(employee=self.emp_profile, date=target_date)
        self.assertTrue(att.is_permission)
        self.assertEqual(att.permission_hours, Decimal('2.00'))

        # Verify audit log
        audit = AttendanceAuditLog.objects.filter(attendance=att, action='PERMISSION_APPROVED').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changed_by, self.hr_user)

        # Verify payroll calculation: 0 deduction
        payroll_data = calculate_payroll_for_employee(self.emp_profile, 2026, 10)
        self.assertEqual(payroll_data['permission_days'], 1)
        self.assertEqual(payroll_data['absent_days'], 0)

    def test_document_submission_and_employee_view(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='emp_john', password='john12345')

        # Employee uploads document and profile picture from profile
        test_file = SimpleUploadedFile("my_doc.pdf", b"sample resume data", content_type="application/pdf")
        test_pic = SimpleUploadedFile("avatar.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00", content_type="image/jpeg")
        resp = self.client.post('/users/profile/', {'update_document': '1', 'document': test_file, 'profile_picture': test_pic}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.emp_profile.refresh_from_db()
        self.assertTrue(self.emp_profile.document)
        self.assertTrue(self.emp_profile.profile_picture)

        # On Employee profile page, employee can view their submitted document and photo
        resp_profile = self.client.get('/users/profile/')
        self.assertEqual(resp_profile.status_code, 200)
        self.assertContains(resp_profile, '📄 View Document')

        # Employee Dashboard displays document and photo submission cards with view links
        resp_dash_get = self.client.get('/dashboard/')
        self.assertEqual(resp_dash_get.status_code, 200)
        self.assertContains(resp_dash_get, 'documentSubmissionSection')
        self.assertContains(resp_dash_get, '📄 View Document')
        self.assertContains(resp_dash_get, 'Official Documents & Profile Picture Submission')

        # Employee can also update document from employee dashboard at any time
        new_file = SimpleUploadedFile("updated_doc.pdf", b"updated resume data", content_type="application/pdf")
        resp_dash = self.client.post('/dashboard/', {'action': 'submit_document', 'document': new_file}, follow=True)
        self.assertEqual(resp_dash.status_code, 200)
        self.emp_profile.refresh_from_db()
        self.assertIn("updated_doc", self.emp_profile.document.name)

        self.client.logout()

        # HR can view the document and details
        self.client.login(username='hr_user', password='hr12345')
        resp_hr = self.client.get(f'/employees/{self.emp_profile.id}/')
        self.assertEqual(resp_hr.status_code, 200)
        self.assertContains(resp_hr, 'View Submitted Document')

    def test_hr_employee_report_export_pdf_excel_zip(self):
        import zipfile
        import io
        self.client.login(username='hr_user', password='hr12345')

        # 1. Export Excel for specific employee
        resp_excel = self.client.get('/reports/complete-export/', {
            'employee_id': self.emp_profile.id,
            'category': 'complete',
            'from_date': '2026-10-01',
            'to_date': '2026-10-31',
            'format': 'excel'
        })
        self.assertEqual(resp_excel.status_code, 200)
        self.assertIn('spreadsheetml.sheet', resp_excel['Content-Type'])
        self.assertIn('attachment', resp_excel['Content-Disposition'])

        # 2. Export PDF for specific employee
        resp_pdf = self.client.get('/reports/complete-export/', {
            'employee_id': self.emp_profile.id,
            'category': 'attendance',
            'from_date': '2026-10-01',
            'to_date': '2026-10-31',
            'format': 'pdf'
        })
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf['Content-Type'], 'application/pdf')
        self.assertTrue(resp_pdf.content.startswith(b'%PDF'))

        # 3. Export ZIP bundle for specific employee (contains PDF, Excel, and README/attachments)
        resp_zip = self.client.get('/reports/complete-export/', {
            'employee_id': self.emp_profile.id,
            'category': 'complete',
            'from_date': '2026-10-01',
            'to_date': '2026-10-31',
            'format': 'zip'
        })
        self.assertEqual(resp_zip.status_code, 200)
        self.assertEqual(resp_zip['Content-Type'], 'application/zip')

        # Verify ZIP contains expected files
        zip_buffer = io.BytesIO(resp_zip.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            namelist = zf.namelist()
            self.assertTrue(any('README_Manifest.txt' in name for name in namelist))
            self.assertTrue(any(name.endswith('.pdf') for name in namelist))
            self.assertTrue(any(name.endswith('.xlsx') for name in namelist))

        # 4. Export all employees company-wide in Excel and PDF
        resp_all_excel = self.client.get('/reports/complete-export/', {
            'category': 'daily_work',
            'from_date': '2026-10-01',
            'to_date': '2026-10-31',
            'format': 'excel'
        })
        self.assertEqual(resp_all_excel.status_code, 200)
        self.assertIn('spreadsheetml.sheet', resp_all_excel['Content-Type'])

        self.client.logout()



