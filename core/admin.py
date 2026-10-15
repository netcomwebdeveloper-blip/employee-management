from django.contrib import admin
from .models import EmployeeProfile, MonthlyLeaveCredit, Attendance, DailyWork, LeaveRequest


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = (
        'employee_code', 'user', 'role', 'department', 'designation',
        'casual_leave_balance', 'is_active_employee'
    )
    search_fields = ('employee_code', 'user__username', 'user__first_name', 'department', 'designation')
    list_filter = ('role', 'department', 'is_active_employee')


@admin.register(MonthlyLeaveCredit)
class MonthlyLeaveCreditAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month', 'casual_added', 'credited_on')
    list_filter = ('year', 'month')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'in_time', 'out_time', 'total_work_time', 'updated_by', 'update_source')
    search_fields = ('employee__employee_code', 'employee__user__username')
    list_filter = ('date', 'update_source')


@admin.register(DailyWork)
class DailyWorkAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'project_name', 'status')
    search_fields = ('employee__employee_code', 'employee__user__username', 'project_name')
    list_filter = ('status', 'date')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'from_date', 'to_date', 'total_days', 'status')
    search_fields = ('employee__employee_code', 'employee__user__username', 'leave_type')
    list_filter = ('status', 'leave_type')
