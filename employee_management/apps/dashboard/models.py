from django.db import models
from django.contrib.auth.models import User

class DashboardBanner(models.Model):
    title = models.CharField(max_length=200, default='Corporate Announcement & Updates')
    image = models.ImageField(upload_to='dashboard_banners/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dashboard Banner'
        verbose_name_plural = 'Dashboard Banners'

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

    @classmethod
    def get_active_banner(cls):
        return cls.objects.filter(is_active=True).first()


class DashboardPopup(models.Model):
    title = models.CharField(max_length=200, default='Netcom Corporate Announcement')
    image = models.ImageField(upload_to='dashboard_popups/')
    description = models.TextField(blank=True, default='')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dashboard Popup'
        verbose_name_plural = 'Dashboard Popups'

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

    @classmethod
    def get_active_popup(cls):
        return cls.objects.filter(is_active=True).first()


class EmployeeMessage(models.Model):
    MESSAGE_TYPES = (
        ('Enquiry', 'General Enquiry'),
        ('Question', 'Policy / Work Question'),
        ('Concern', 'Work-Related Concern'),
        ('Request', 'Workplace Request'),
        ('Other', 'Other Feedback / Message'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending / Unread'),
        ('In Review', 'In Review'),
        ('Replied', 'Replied / Resolved'),
        ('Closed', 'Closed'),
    )

    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='sent_messages')
    category = models.CharField(max_length=50, choices=MESSAGE_TYPES, default='Enquiry')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    # HR management & response
    hr_response = models.TextField(blank=True, default='')
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_message_responses')
    responded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Employee Message'
        verbose_name_plural = 'Employee Messages'

    def __str__(self):
        return f"{self.employee.employee_code} - {self.subject} ({self.status})"

    @property
    def responder_name(self):
        if self.responded_by:
            full = self.responded_by.get_full_name()
            return full if full else self.responded_by.username
        return "HR Department"


