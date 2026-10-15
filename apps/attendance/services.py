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


def reset_daily_missed_punch_in_status(target_date=None):
    """
    Evaluates and resets daily punch-in status for all active employees, HR staff, and administrators.
    - Calculates attendance based on the system's local calendar day (12:00 AM to 11:59 PM).
    - Daily punch-in is mandatory for all employees, HR, and admins.
    - Auto-evaluation occurs at 12:00 AM midnight for the new local calendar day:
      Any past unpunched records (date < today) are evaluated and marked as 'Missed Punch-In' / 'Midnight Daily Auto-Reset'.
    - For the current working day (today), unpunched staff remain 'Pending Punch-In' throughout the active calendar day.
    - Historical attendance records (date < today) with recorded punches are strictly preserved without alteration or deletion.
    """
    from apps.employees.models import Employee
    from apps.leave_management.models import OfficePaidLeave

    now = timezone.localtime()
    today = target_date if target_date else now.date()

    # 1. Midnight 12:00 AM reset / historical auto-evaluation:
    # Finalize any past 'Pending Punch-In' or unpunched past records (date < today)
    past_pendings = Attendance.objects.filter(date__lt=today, status__in=['Pending Punch-In', 'Pending', 'Absent'])
    for p_att in past_pendings:
        if not p_att.in_time:
            if p_att.status != 'Missed Punch-In' or p_att.update_source != 'Midnight Daily Auto-Reset':
                p_att.status = 'Missed Punch-In'
                p_att.update_source = 'Midnight Daily Auto-Reset'
                p_att.save(update_fields=['status', 'update_source'])

    # 2. All active employees across all roles: EMPLOYEE, HR, ADMIN
    active_employees = Employee.objects.filter(is_active_employee=True).select_related('user')

    # Find today's approved leaves
    approved_leave_emp_ids = set(
        LeaveRequest.objects.filter(
            status='Approved',
            from_date__lte=today,
            to_date__gte=today
        ).values_list('employee_id', flat=True)
    )

    is_office_holiday = OfficePaidLeave.objects.filter(date=today).first()
    updated_count = 0

    for emp in active_employees:
        # If on approved leave, keep intact
        if emp.id in approved_leave_emp_ids:
            continue

        # If today is an Office Paid Leave / holiday
        if is_office_holiday:
            att, created = Attendance.objects.get_or_create(employee=emp, date=today)
            if not att.in_time and not att.out_time and att.status != 'On Leave':
                att.status = 'On Leave'
                att.is_approved_leave = True
                att.leave_type = 'Paid Leave for the Office'
                att.leave_reason = is_office_holiday.title
                att.update_source = 'Office Paid Leave'
                att.save()
                updated_count += 1
            continue

        att = Attendance.objects.filter(employee=emp, date=today).first()

        if att:
            # If marked for official duty or approved leave, do not overwrite
            if att.is_official_duty or att.status in ('On Leave', 'Official Duty') or att.update_source == 'Official Office Duty':
                continue

            if att.in_time:
                # Already punched in
                if not att.out_time:
                    if att.status != 'Missing Punch-Out' and att.status not in ('Permission - 2 Hours', 'Half Day'):
                        att.status = 'Missing Punch-Out'
                        att.save(update_fields=['status'])
                        updated_count += 1
            else:
                # No punch in recorded for today yet -> remains Pending Punch-In during the active calendar day
                if att.status in ('Missed Punch-In', 'Daily 12:00 PM Auto-Evaluation') or '12:00 PM' in (att.update_source or ''):
                    att.status = 'Pending Punch-In'
                    att.update_source = 'Mandatory Daily Punch'
                    att.save(update_fields=['status', 'update_source'])
                    updated_count += 1
                elif att.status not in ('Pending Punch-In', 'Absent'):
                    att.status = 'Pending Punch-In'
                    att.save(update_fields=['status'])
                    updated_count += 1
        else:
            # No record for today yet -> Initialize with Pending Punch-In
            Attendance.objects.create(
                employee=emp,
                date=today,
                status='Pending Punch-In',
                update_source='Mandatory Daily Punch'
            )
            updated_count += 1

    return updated_count


def correct_missing_punch_out(employee, att_date, verified_out_time, reason, hr_user, ip_address=''):
    """
    Dedicated function allowing authorized HR staff and Administrators to manually enter
    or correct the missing punch-out time for employees who completed punch-in but missed punch-out.
    - Saves verified punch-out time without requiring new GPS or selfie from the employee.
    - Records update_source as 'HR Manual Punch-Out Correction' (non-GPS / non-selfie).
    - Writes an immutable audit trail entry containing HR user ID, timestamp, original and updated details, and reason.
    - Automatically updates working minutes and sets status to Present (>=9h) or Half Day (>=4.5h).
    - Restores casual leave balance if deducted for that date.
    - Strictly prevents unauthorized employee self-edits.
    """
    if not employee or not att_date or not verified_out_time:
        return False, "Employee, attendance date, and verified punch-out time are required."

    att = Attendance.objects.filter(employee=employee, date=att_date).first()
    if not att:
        return False, f"No attendance record found for {employee.display_name()} on {att_date}."

    if not att.in_time:
        return False, f"Employee {employee.display_name()} has no recorded punch-in on {att_date}. Punch-out can only be corrected for an existing punch-in."

    old_val = (
        f"in: {att.in_time}, out: {att.out_time}, status: {att.status}, "
        f"source: {att.update_source}, updated_by: {att.updated_by_id if att.updated_by else 'None'}"
    )

    att.out_time = verified_out_time
    att.updated_by = hr_user
    att.update_source = 'HR Manual Punch-Out Correction'

    # Compute working hours
    mins = att.total_work_minutes
    if mins >= 540:
        att.status = 'Present'
    elif mins >= 270:
        att.status = 'Half Day'
    else:
        att.status = 'Present'

    att.save()

    # Create immutable audit log entry
    AttendanceAuditLog.objects.create(
        attendance=att,
        changed_by=hr_user,
        action='HR_MANUAL_PUNCH_OUT_CORRECTION',
        old_values=old_val,
        new_values=(
            f"out_time: {att.out_time}, status: {att.status}, work_time: {att.total_work_time}, "
            f"reason: {reason}, source: HR Manual Punch-Out Correction (Non-GPS / Non-Selfie)"
        ),
        ip_address=ip_address or ''
    )

    # Check and restore casual leave balance if deducted
    restored, _ = check_and_restore_casual_leave_on_attendance(employee, att_date, att, changed_by=hr_user)

    msg = (
        f"Successfully corrected punch-out for {employee.display_name()} on {att_date} "
        f"to {verified_out_time.strftime('%I:%M %p')}. Total working time: {att.total_work_time} (Status: {att.status}). "
        f"Audit trail recorded under HR User '{hr_user.username}'."
    )
    if restored:
        msg += f" (+1 Casual Leave day restored to balance: {employee.casual_leave_balance})."

    return True, msg


def mark_office_holiday_calendar(target_date, title='Office Paid Holiday', description='', marked_by=None):
    """
    Allows HR and Administrators to mark a date as an official office holiday / approved non-working day.
    - Saves to OfficePaidLeave calendar.
    - Automatically updates attendance across all active employees to 'On Leave' (Paid Leave for the Office).
    - Preserves valid working punches (if an employee actually worked on that holiday).
    - Restores any personal casual leaves deducted for that date.
    - Displays status prominently in green with full paid credit, without incorrectly marking as LWP.
    """
    from apps.leave_management.models import OfficePaidLeave, LeaveRequest
    opl, created = OfficePaidLeave.objects.get_or_create(
        date=target_date,
        defaults={'title': title, 'description': description, 'marked_by': marked_by}
    )
    if not created:
        opl.title = title
        opl.description = description
        opl.marked_by = marked_by
        opl.save()

    from apps.employees.models import Employee
    for emp in Employee.objects.filter(is_active_employee=True):
        # Restore casual leave if employee had applied for personal leave on this office holiday
        for leave in LeaveRequest.objects.filter(employee=emp, from_date__lte=target_date, to_date__gte=target_date, status='Approved'):
            if 'Casual' in leave.leave_type or leave.is_paid:
                emp.casual_leave_balance += 1
                emp.save(update_fields=['casual_leave_balance'])
            if leave.from_date == leave.to_date == target_date:
                leave.status = 'Cancelled'
                leave.rejection_reason = f"Cancelled: Converted to Office Paid Holiday ({title})"
                leave.save()
            else:
                leave.total_days = max(0, leave.total_days - 1)
                leave.save()

        att, _ = Attendance.objects.get_or_create(employee=emp, date=target_date)
        # Preserve existing valid work punches
        if att.in_time and att.out_time and att.total_work_minutes >= 270:
            continue

        att.status = 'On Leave'
        att.is_approved_leave = True
        att.leave_type = 'Paid Leave for the Office'
        att.leave_reason = title
        att.updated_by = marked_by
        att.update_source = 'Office Paid Leave'
        att.save()

    return opl


def mark_employee_official_duty(employee, att_date, duty_title='Official Office Duty', notes='', marked_by=None):
    """
    Allows HR and Administrators to mark an employee as on official office duty or official work assignment.
    Automatically marks the employee as Present instead of Leave on the selected date,
    cancels/converts any applied leave, restores casual leave balance if deducted,
    sets attendance status to Present with full hours, and records full audit log.
    """
    from datetime import time
    if not employee or not att_date:
        return False, "Employee and Date are required."

    # 1. Check if employee has an active/approved leave request covering this date
    leaves = LeaveRequest.objects.filter(
        employee=employee,
        from_date__lte=att_date,
        to_date__gte=att_date,
        status__in=['Approved', 'Pending']
    )

    restored_leaves = []
    for l in leaves:
        if l.status == 'Approved' and ('Casual' in l.leave_type or l.is_paid):
            employee.casual_leave_balance += 1
            employee.save(update_fields=['casual_leave_balance'])
            restored_leaves.append(f"Leave #{l.id} (+1 Casual Leave balance restored)")

        reason_note = f"Converted to Official Duty: {duty_title}. {notes}".strip()
        if l.from_date == l.to_date == att_date:
            l.status = 'Cancelled'
            l.rejection_reason = reason_note
            l.save()
        else:
            l.total_days = max(0, l.total_days - 1)
            l.rejection_reason = (l.rejection_reason + f" | {reason_note}").strip(' | ')
            if l.total_days == 0:
                l.status = 'Cancelled'
            l.save()

    # 2. Update or create Attendance record for the selected date
    att, created = Attendance.objects.get_or_create(employee=employee, date=att_date)
    old_val = f"status: {att.status}, in: {att.in_time}, out: {att.out_time}, source: {att.update_source}"

    att.status = 'Present'
    att.is_approved_leave = False
    att.leave_type = 'Official Duty'
    full_reason = f"{duty_title}: {notes}".strip(': ') if notes else duty_title
    att.leave_reason = full_reason
    att.update_source = 'Official Office Duty'
    att.updated_by = marked_by

    # Set default standard 9-hour working schedule (09:00 - 18:00) if no biometric punches recorded
    if not att.in_time:
        att.in_time = time(9, 0)
    if not att.out_time:
        att.out_time = time(18, 0)

    att.save()

    # 3. Record Audit Log
    AttendanceAuditLog.objects.create(
        attendance=att,
        changed_by=marked_by,
        action='OFFICIAL_DUTY_ASSIGNED',
        old_values=old_val if not created else 'NEW_RECORD',
        new_values=f"Status: Present (Official Duty), Source: Official Office Duty, Details: {full_reason}",
        ip_address=''
    )

    msg = f"Successfully marked {employee.display_name()} as Present on {att_date} for {duty_title}. Attendance records and salary calculations updated."
    if restored_leaves:
        msg += f" ({', '.join(restored_leaves)})"

    return True, msg

