import os
from io import BytesIO
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.employees.models import Employee
from apps.attendance.models import DailyWork
from apps.dashboard.models import DashboardPopup, DashboardBanner


class PopupAndScreenshotUploadTestCase(TestCase):
    def setUp(self):
        # Create active popup
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        uploaded_popup = SimpleUploadedFile('popup_test.jpg', img_io.read(), content_type='image/jpeg')
        self.popup = DashboardPopup.objects.create(
            title='Test Corporate Announcement',
            image=uploaded_popup,
            description='Test announcement popup content',
            is_active=True
        )

        # Create active banner
        banner_io = BytesIO()
        img.save(banner_io, format='JPEG')
        banner_io.seek(0)
        uploaded_banner = SimpleUploadedFile('banner_test.jpg', banner_io.read(), content_type='image/jpeg')
        self.banner = DashboardBanner.objects.create(
            title='Netcom Header Banner',
            image=uploaded_banner,
            is_active=True
        )

        # Create test employee
        self.user = User.objects.create_user(username='testemp', password='password123', first_name='Test', last_name='Employee')
        self.employee = Employee.objects.create(
            user=self.user,
            employee_code='EMPTEST99',
            role='EMPLOYEE',
            joining_date='2026-01-01',
            basic_salary=30000.00
        )
        self.client = Client()

    def test_popup_lifecycle_on_login_and_navigation(self):
        """Tests that popup shows ONLY on dashboard entry after login, and not across navigation or refreshes."""
        # 1. Login page before login should not have active popup
        resp = self.client.get('/login/')
        self.assertNotContains(resp, 'announcement-popup-overlay active')

        # 2. Login
        login_resp = self.client.post('/login/', {'username': 'testemp', 'password': 'password123'})
        self.assertEqual(login_resp.status_code, 302)

        # 3. Enter Dashboard for the first time after login -> Popup should be ACTIVE
        dash_resp = self.client.get('/dashboard/')
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, 'globalAnnouncementModal')
        self.assertContains(dash_resp, 'announcement-popup-overlay active')

        # 4. Refresh Dashboard -> Popup should NOT be active
        refresh_resp = self.client.get('/dashboard/')
        self.assertNotContains(refresh_resp, 'announcement-popup-overlay active')

        # 5. Navigate to Daily Works -> Popup should NOT be active
        daily_resp = self.client.get('/attendance/daily-work/')
        self.assertEqual(daily_resp.status_code, 200)
        self.assertNotContains(daily_resp, 'announcement-popup-overlay active')

        # 6. Navigate to Profile -> Popup should NOT be active
        prof_resp = self.client.get('/users/profile/')
        self.assertEqual(prof_resp.status_code, 200)
        self.assertNotContains(prof_resp, 'announcement-popup-overlay active')

        # 7. Navigate to Leave -> Popup should NOT be active
        leave_resp = self.client.get('/leave/')
        self.assertEqual(leave_resp.status_code, 200)
        self.assertNotContains(leave_resp, 'announcement-popup-overlay active')

        # 8. Return to Dashboard -> Popup should NOT be active
        return_resp = self.client.get('/dashboard/')
        self.assertEqual(return_resp.status_code, 200)
        self.assertNotContains(return_resp, 'announcement-popup-overlay active')

        # 9. Logout -> Redirects to login
        logout_resp = self.client.get('/logout/')
        self.assertEqual(logout_resp.status_code, 302)

        login_after_logout = self.client.get('/login/')
        self.assertNotContains(login_after_logout, 'announcement-popup-overlay active')

        # 10. Login again -> Popup should show once again on dashboard
        self.client.post('/login/', {'username': 'testemp', 'password': 'password123'})
        second_dash = self.client.get('/dashboard/')
        self.assertContains(second_dash, 'announcement-popup-overlay active')

    def test_daily_work_screenshot_upload_valid(self):
        """Tests uploading a valid screenshot with Daily Work submission."""
        self.client.login(username='testemp', password='password123')

        # Create test screenshot
        img = Image.new('RGB', (300, 300), color='green')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        screenshot = SimpleUploadedFile('daily_task_screenshot.png', img_io.read(), content_type='image/png')

        resp = self.client.post('/attendance/daily-work/', {
            'project_name': 'Backend API Fix',
            'work_details': 'Implemented and tested the screenshot upload and popup flow',
            'status': 'Completed',
            'work_image': screenshot,
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'uploaded successfully')

        # Check DB record
        work = DailyWork.objects.filter(employee=self.employee, project_name='Backend API Fix').first()
        self.assertIsNotNone(work)
        self.assertTrue(bool(work.work_image))
        self.assertTrue(os.path.exists(work.work_image.path))

        # Check rendered screenshot elements in response HTML
        self.assertContains(resp, work.work_image.url)
        self.assertContains(resp, 'work-thumb')
        self.assertContains(resp, 'openWorkImageModal')
        self.assertContains(resp, 'View Full Screenshot')

    def test_daily_work_invalid_file_format_rejected(self):
        """Tests that non-image formats are rejected with a clear validation error."""
        self.client.login(username='testemp', password='password123')

        bad_file = SimpleUploadedFile('script.py', b'print("hello")', content_type='text/x-python')
        resp = self.client.post('/attendance/daily-work/', {
            'project_name': 'Invalid Extension Test',
            'work_details': 'Attempting upload with non-image file',
            'status': 'Pending',
            'work_image': bad_file,
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Unsupported image format')
        self.assertFalse(DailyWork.objects.filter(project_name='Invalid Extension Test').exists())

    def test_daily_work_oversized_file_rejected(self):
        """Tests that oversized images (> 10MB) are rejected with a clear validation error."""
        self.client.login(username='testemp', password='password123')

        oversized_bytes = b'X' * (11 * 1024 * 1024)
        huge_file = SimpleUploadedFile('massive.png', oversized_bytes, content_type='image/png')
        resp = self.client.post('/attendance/daily-work/', {
            'project_name': 'Oversized Image Test',
            'work_details': 'Attempting upload with 11MB file',
            'status': 'Pending',
            'work_image': huge_file,
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'less than 10MB')
        self.assertFalse(DailyWork.objects.filter(project_name='Oversized Image Test').exists())

    def test_daily_work_without_image_succeeds(self):
        """Tests that daily work can be submitted without an image (optional attachment)."""
        self.client.login(username='testemp', password='password123')

        resp = self.client.post('/attendance/daily-work/', {
            'project_name': 'Optional Image Test',
            'work_details': 'Submitted work report without attaching a screenshot',
            'status': 'In Progress',
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Daily work report submitted successfully')
        self.assertTrue(DailyWork.objects.filter(project_name='Optional Image Test').exists())
