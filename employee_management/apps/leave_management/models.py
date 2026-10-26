from django.db import models
from django.contrib.auth.models import User
from apps.employees.models import Employee

class LeaveRequest(models.Model):
    LEAVE_TYPES = (
        ('Casual Leave', 'Casual Leave'),
        ('Sick Leave', 'Sick Leave'),
        ('Permission (Up to 2 Hours)', 'Permission (Up to 2 Hours)'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES, default='Casual Leave')
    from_date = models.DateField()
    to_date = models.DateField()
    total_days = models.PositiveIntegerField(default=1)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    applied_on = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    rejection_reason = models.TextField(blank=True)
    is_paid = models.BooleanField(default=True, help_text="True if Paid Casual/Annual/Sick Leave, False if Unpaid Leave")
    approval_type = models.CharField(max_length=50, blank=True, default='Paid Casual Leave')

    class Meta:
        ordering = ['-applied_on', '-id']
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'

    def save(self, *args, **kwargs):
        if self.from_date and self.to_date:
            f_date = self.from_date
            t_date = self.to_date
            if isinstance(f_date, str):
                from datetime import datetime
                f_date = datetime.strptime(f_date[:10], '%Y-%m-%d').date()
            if isinstance(t_date, str):
                from datetime import datetime
                t_date = datetime.strptime(t_date[:10], '%Y-%m-%d').date()
            self.total_days = max(1, (t_date - f_date).days + 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type} ({self.status})"


class HRNotification(models.Model):
    recipient_role = models.CharField(max_length=20, default='HR')
    title = models.CharField(max_length=150)
    message = models.TextField()
    leave_request = models.ForeignKey(LeaveRequest, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'HR Notification'
        verbose_name_plural = 'HR Notifications'

    def __str__(self):
        return f"{self.title} ({'Read' if self.is_read else 'Unread'})"


class MonthlyLeaveCredit(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='monthly_credits')
    year = models.IntegerField()
    month = models.IntegerField()
    casual_added = models.PositiveIntegerField(default=1)
    credited_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'year', 'month')
        verbose_name = 'Monthly Leave Credit'
        verbose_name_plural = 'Monthly Leave Credits'

    def __str__(self):
        return f"{self.employee.employee_code} - {self.month}/{self.year}"


class OfficePaidLeave(models.Model):
    date = models.DateField(unique=True, help_text="Date marked as office-wide paid leave")
    title = models.CharField(max_length=150, default='Office Paid Leave')
    description = models.TextField(blank=True, default='')
    marked_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='office_paid_leaves')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Office Paid Leave'
        verbose_name_plural = 'Office Paid Leaves'

    def __str__(self):
        return f"{self.date} - {self.title}"


class MonthlyPermissionBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='permission_balances')
    year = models.IntegerField()
    month = models.IntegerField()
    total_hours_allowed = models.DecimalField(max_digits=4, decimal_places=2, default=1.0 * 5.0, help_text="Total permission hours allowed per month (Default 5.00 hours)")
    used_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, help_text="Approved permission hours used in this month")
    total_requests_allowed = models.PositiveIntegerField(default=2, help_text="Maximum permission requests allowed per month (Default 2)")
    used_requests_count = models.PositiveIntegerField(default=0, help_text="Number of approved permission requests in this month")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'year', 'month')
        verbose_name = 'Monthly Permission Balance'
        verbose_name_plural = 'Monthly Permission Balances'

    def __str__(self):
        return f"{self.employee.employee_code} - {self.month}/{self.year} (Rem: {self.remaining_formatted()}, Reqs: {self.remaining_requests})"

    @property
    def remaining_hours(self):
        from decimal import Decimal
        rem = Decimal(str(self.total_hours_allowed)) - Decimal(str(self.used_hours))
        return max(Decimal('0.00'), rem)

    @property
    def remaining_requests(self):
        return max(0, self.total_requests_allowed - self.used_requests_count)

    def remaining_formatted(self):
        rem = float(self.remaining_hours)
        hours = int(rem)
        minutes = int(round((rem - hours) * 60))
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        elif minutes > 0:
            return f"{minutes}m"
        return "0h"
