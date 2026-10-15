from django.db import models
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils import timezone


class EmployeeProfile(models.Model):
    ROLE_CHOICES = (
        ('EMPLOYEE', 'Employee'),
        ('HR', 'HR'),
        ('ADMIN', 'Admin'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_code = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    joining_date = models.DateField(default=timezone.localdate)
    is_active_employee = models.BooleanField(default=True)

    casual_leave_balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.employee_code} - {self.user.get_full_name() or self.user.username}"

    def display_name(self):
        return self.user.get_full_name() or self.user.username


class MonthlyLeaveCredit(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    casual_added = models.PositiveIntegerField(default=1)
    credited_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'year', 'month')

    def __str__(self):
        return f"{self.employee.employee_code} - {self.month}/{self.year}"


class Attendance(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    in_time = models.TimeField(null=True, blank=True)
    out_time = models.TimeField(null=True, blank=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    update_source = models.CharField(max_length=30, default='Manual')

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date', '-id']

    @property
    def total_work_time(self):
        if not self.in_time or not self.out_time:
            return "-"

        start = datetime.combine(self.date, self.in_time)
        end = datetime.combine(self.date, self.out_time)

        # If out time is after midnight / next day
        if end < start:
            end = end + timedelta(days=1)

        total = end - start
        total_minutes = int(total.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        return f"{hours}h {minutes}m"

    def __str__(self):
        return f"{self.employee.user.username} - {self.date}"


class DailyWork(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    )

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    project_name = models.CharField(max_length=150)
    work_details = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.employee.user.username} - {self.project_name}"


class LeaveRequest(models.Model):
    LEAVE_TYPES = (
        ('Casual Leave', 'Casual Leave'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES)
    from_date = models.DateField()
    to_date = models.DateField()
    total_days = models.PositiveIntegerField(default=1)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    applied_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_on']

    def save(self, *args, **kwargs):
        if self.from_date and self.to_date:
            self.total_days = (self.to_date - self.from_date).days + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.user.username} - {self.leave_type} - {self.status}"
