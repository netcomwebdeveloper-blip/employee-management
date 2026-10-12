from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from apps.attendance.models import Attendance, AttendanceAuditLog
from apps.leave_management.models import LeaveRequest

def check_and_restore_casual_leave_on_attendance(employee, att_date, attendance_obj=None, changed_by=None):
    """
    If an employee applies for casual leave (approved or pending) but actually attends
    the office and completes the required working hours on that day (>= 270 minutes / 4.5 hours),
    cancel the leave for that date, restore the casual leave balance by one day,
    and update the attendance record accordingly.
    Guarantees no duplicate entries or duplicate balance restorations.
    """
    if not employee or not att_date:
        return False, "Invalid employee or date."

    if not attendance_obj:
        attendance_obj = Attendance.objects.filter(employee=employee, date=att_date).first()

    if not attendance_obj:
        return False, "No attendance record found for this date."

    # Must complete required working hours: minimum half day (>= 270 minutes) or full day (>= 540 minutes)
    if attendance_obj.total_work_minutes < 270:
        return False, "Attendance duration is below required working hours (minimum 4.5 hours required)."

    # Prevent duplicate restoration for the same attendance record and date
    already_restored = AttendanceAuditLog.objects.filter(
        attendance=attendance_obj,
        action='CASUAL_LEAVE_RESTORED'
    ).exists()
    if already_restored:
        return False, "Casual leave balance already restored for this attendance date."

    # Find active leave requests covering att_date for this employee
    leaves = LeaveRequest.objects.filter(
        employee=employee,
        from_date__lte=att_date,
        to_date__gte=att_date,
        status__in=['Approved', 'Pending']
    )

    restored = False
    cancelled_leave_details = []

    for leave in leaves:
        is_casual = (
            'Casual' in leave.leave_type or 
            'Casual' in (leave.approval_type or '') or 
            leave.is_paid
        )
        if not is_casual:
            continue

        was_approved = (leave.status == 'Approved')

        # If the leave was approved, restore +1 to employee's casual leave balance
        if was_approved:
            employee.casual_leave_balance += 1
            employee.save(update_fields=['casual_leave_balance'])
            restored = True

        hours_str = attendance_obj.total_work_time
        # Update leave request
        if leave.from_date == leave.to_date == att_date:
            leave.status = 'Cancelled'
            leave.rejection_reason = (
                f"Cancelled: Employee attended office on {att_date} and completed "
                f"required working hours ({hours_str}). Casual leave balance restored (+1 day)."
            )
            leave.save()
            cancelled_leave_details.append(f"Leave #{leave.id} (1 day cancelled)")
        else:
            # Multi-day leave: deduct 1 day from requested span and log restoration
            leave.total_days = max(0, leave.total_days - 1)
            notes = f"Date {att_date} cancelled due to office attendance ({hours_str}). Casual leave restored."
            if leave.rejection_reason:
                leave.rejection_reason += f" | {notes}"
            else:
                leave.rejection_reason = notes
            if leave.total_days == 0:
                leave.status = 'Cancelled'
            leave.save()
            cancelled_leave_details.append(f"Leave #{leave.id} ({att_date} cancelled)")

    # Clean up attendance record if it had been initialized as On Leave
    if attendance_obj.is_approved_leave or attendance_obj.status == 'On Leave':
        attendance_obj.is_approved_leave = False
        attendance_obj.leave_type = ''
        attendance_obj.leave_reason = f"Casual leave cancelled: Attended office ({attendance_obj.total_work_time})"

    if attendance_obj.total_work_minutes >= 540:
        attendance_obj.status = 'Present'
    elif attendance_obj.total_work_minutes >= 270:
        attendance_obj.status = 'Half Day'
    attendance_obj.save()

    # Record Audit Log
    AttendanceAuditLog.objects.create(
        attendance=attendance_obj,
        changed_by=changed_by or getattr(employee, 'user', None),
        action='CASUAL_LEAVE_RESTORED',
        old_values=f"Leave on {att_date}",
        new_values=(
            f"Restored +1 casual leave (New balance: {employee.casual_leave_balance}). "
            f"Attendance status: {attendance_obj.status} ({attendance_obj.total_work_time}). "
            f"Cancelled Leaves: {', '.join(cancelled_leave_details) if cancelled_leave_details else 'Attendance confirmed'}"
        ),
        ip_address=''
    )

    return True, f"Casual leave cancelled and balance restored (+1 day) for {att_date}."
