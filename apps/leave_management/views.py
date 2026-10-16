from decimal import Decimal
import re
from datetime import timedelta, datetime, time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from apps.users.decorators import hr_or_admin_required
from apps.attendance.models import Attendance, AttendanceAuditLog
from .models import LeaveRequest, MonthlyLeaveCredit, MonthlyPermissionBalance, HRNotification
from .forms import LeaveRequestForm

def get_or_create_monthly_permission_balance(employee, year=None, month=None):
    """
    Retrieves or initializes the monthly permission balance for an employee.
    Each employee receives a maximum of 5.00 hours and 2 requests per calendar month.
    Resets at the start of each month.
    """
    if not employee:
        return None
    today = timezone.localdate()
    y = int(year) if year else today.year
    m = int(month) if month else today.month

    balance, created = MonthlyPermissionBalance.objects.get_or_create(
        employee=employee,
        year=y,
        month=m,
        defaults={
            'total_hours_allowed': Decimal('5.00'),
            'used_hours': Decimal('0.00'),
            'total_requests_allowed': 2,
            'used_requests_count': 0
        }
    )
    return balance

def refresh_all_active_employees_monthly_permission():
    """
    Initializes/refreshes monthly permission balances for all active employees.
    """
    today = timezone.localdate()
    from apps.employees.models import Employee
    for emp in Employee.objects.filter(is_active_employee=True):
        get_or_create_monthly_permission_balance(emp, today.year, today.month)

def refresh_monthly_leave_for_employee(employee, today=None):
    """
    Refreshes an employee's casual leave balance to exactly 1 casual leave per month
    at the beginning of every month.
    Casual leave does NOT carry forward from one month to the next.
    Any unused casual leave from the previous month is not carried forward.
    Current month approved casual leaves are deducted from the 1-day allowance.
    """
    if not employee or not employee.is_active_employee:
        return False
    if today is None:
        today = timezone.localdate()

    credit, created = MonthlyLeaveCredit.objects.get_or_create(
        employee=employee,
        year=today.year,
        month=today.month,
        defaults={'casual_added': 1}
    )

    # Also ensure monthly permission balance exists
    get_or_create_monthly_permission_balance(employee, today.year, today.month)

    if created:
        # New month reset: refresh to strictly 1 casual leave per month, zero carry-forward
        employee.casual_leave_balance = 1
        employee.save(update_fields=['casual_leave_balance'])
        return True
    elif employee.casual_leave_balance > 1:
        # Eliminate legacy carried-forward balances exceeding monthly allowance
        employee.casual_leave_balance = 1
        employee.save(update_fields=['casual_leave_balance'])
        return True
    return False

def refresh_all_active_employees_monthly_leave():
    """
    Refreshes monthly casual leave balance for all active employees (1/month, no carry-forward).
    """
    today = timezone.localdate()
    from apps.employees.models import Employee
    for emp in Employee.objects.filter(is_active_employee=True):
        refresh_monthly_leave_for_employee(emp, today)
        get_or_create_monthly_permission_balance(emp, today.year, today.month)

# Backward compatibility alias
auto_credit_monthly_leave = refresh_monthly_leave_for_employee

@login_required
def leave_list(request):
    profile = getattr(request.user, 'employee', None)
    perm_balance = None
    if profile:
        refresh_monthly_leave_for_employee(profile)
        perm_balance = get_or_create_monthly_permission_balance(profile)

    is_management = profile and (profile.role in ('ADMIN', 'HR') or request.user.is_superuser)

    if is_management:
        status_filter = request.GET.get('status', '')
        requests_qs = LeaveRequest.objects.select_related('employee', 'employee__user', 'employee__department').all()
        if status_filter:
            requests_qs = requests_qs.filter(status=status_filter)
    else:
        requests_qs = LeaveRequest.objects.filter(employee=profile)

    apply_form = LeaveRequestForm()
    if request.method == 'POST':
        leave_type_val = request.POST.get('leave_type', '')
        if leave_type_val in ('Permission (Up to 2 Hours)', 'Permission'):
            perm_date_str = request.POST.get('permission_date') or request.POST.get('from_date', '')
            from_time_str = request.POST.get('from_time', '').strip()
            to_time_str = request.POST.get('to_time', '').strip()
            reason = request.POST.get('reason', '').strip()

            if not perm_date_str or not from_time_str or not to_time_str or not reason:
                messages.error(request, "Date, From Time, To Time, and Reason are all mandatory for Permission requests.")
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            try:
                perm_date = datetime.strptime(perm_date_str[:10], '%Y-%m-%d').date()
                fh, fm = [int(p) for p in from_time_str.split(':')[:2]]
                th, tm = [int(p) for p in to_time_str.split(':')[:2]]
                f_mins = fh * 60 + fm
                t_mins = th * 60 + tm
            except Exception:
                messages.error(request, "Invalid date or time format provided for permission request.")
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            diff_mins = t_mins - f_mins
            if diff_mins <= 0:
                messages.error(request, "Invalid time range: To Time must be after From Time.")
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            # Minimum 30 minutes validation
            if diff_mins < 30:
                messages.error(request, "Permission limit: Minimum allowed duration is 30 minutes.")
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            # Maximum 2 hours (120 minutes) per day validation
            if diff_mins > 120:
                messages.error(request, "Permission limit exceeded: Maximum allowed duration is 2 hours (120 minutes) per day.")
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            # Validate date is not before employee's joining date
            if profile.joining_date and perm_date < profile.joining_date:
                messages.error(
                    request,
                    f"Invalid date: You cannot request permission for {perm_date.strftime('%b %d, %Y')}, "
                    f"which is before your official joining date ({profile.joining_date.strftime('%b %d, %Y')})."
                )
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            # Check monthly permission balance and request limits
            month_balance = get_or_create_monthly_permission_balance(profile, perm_date.year, perm_date.month)
            if month_balance.remaining_requests <= 0:
                messages.error(
                    request,
                    f"Monthly permission limit reached: Maximum 2 permission requests allowed per calendar month. "
                    f"You have 0 requests remaining for {perm_date.strftime('%B %Y')}."
                )
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            req_hours = Decimal(str(round(diff_mins / 60.0, 2)))
            if req_hours > month_balance.remaining_hours:
                messages.error(
                    request,
                    f"Requested duration ({diff_mins} mins / {req_hours}h) exceeds your remaining monthly permission balance "
                    f"({month_balance.remaining_formatted()} remaining out of 5 hours for {perm_date.strftime('%B %Y')})."
                )
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            # Prevent duplicate / overlapping permission requests for the same date
            existing = LeaveRequest.objects.filter(
                employee=profile,
                from_date=perm_date,
                leave_type__in=['Permission', 'Permission (Up to 2 Hours)'],
                status__in=['Pending', 'Approved']
            ).first()

            if existing:
                messages.error(
                    request,
                    f"A permission request for {perm_date.strftime('%b %d, %Y')} is already {existing.status.lower()}. "
                    "Only one permission request per working day is allowed."
                )
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            t_from = time(fh, fm)
            t_to = time(th, tm)
            dur_str = f"{diff_mins // 60}h {diff_mins % 60}m" if diff_mins >= 60 else f"{diff_mins} mins"

            leave = LeaveRequest.objects.create(
                employee=profile,
                leave_type='Permission (Up to 2 Hours)',
                from_date=perm_date,
                to_date=perm_date,
                total_days=1,
                is_paid=True,
                approval_type=f"Permission ({dur_str})",
                reason=f"Permission: {t_from.strftime('%I:%M %p')} to {t_to.strftime('%I:%M %p')} ({dur_str}) — {reason}",
                status='Pending'
            )

            HRNotification.objects.create(
                recipient_role='HR',
                title=f"New Permission Request from {profile.display_name()}",
                message=(
                    f"{profile.display_name()} ({profile.employee_code}) submitted a permission request for "
                    f"{perm_date.strftime('%b %d, %Y')} from {t_from.strftime('%I:%M %p')} to {t_to.strftime('%I:%M %p')} "
                    f"({dur_str}). Reason: {reason}"
                ),
                leave_request=leave
            )

            messages.success(request, f"Permission request for {dur_str} on {perm_date.strftime('%b %d, %Y')} submitted for HR approval! (Remaining: {month_balance.remaining_formatted()} / {month_balance.remaining_requests} requests)")
            return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

        apply_form = LeaveRequestForm(request.POST)
        if apply_form.is_valid():
            leave = apply_form.save(commit=False)
            leave.employee = profile
            leave.total_days = max(1, (leave.to_date - leave.from_date).days + 1)

            leave.save()

            # Automatically notify the HR department
            HRNotification.objects.create(
                recipient_role='HR',
                title=f"New Leave Request from {profile.display_name()}",
                message=(
                    f"{profile.display_name()} ({profile.employee_code}) has submitted a {leave.leave_type} request "
                    f"for {leave.total_days} day(s) from {leave.from_date} to {leave.to_date}. Reason: {leave.reason}"
                ),
                leave_request=leave
            )

            messages.success(request, f"{leave.leave_type} application for {leave.total_days} day(s) submitted for approval. The HR department has been notified.")
            return redirect('leave_management:list')
        else:
            for err_list in apply_form.errors.values():
                for err in err_list:
                    messages.error(request, err)

    pending_count = LeaveRequest.objects.filter(status='Pending').count() if is_management else 0
    hr_notifications = HRNotification.objects.filter(is_read=False)[:10] if is_management else []

    context = {
        'leaves': requests_qs[:100],
        'apply_form': apply_form,
        'profile': profile,
        'is_management': is_management,
        'pending_count': pending_count,
        'hr_notifications': hr_notifications,
    }
    return render(request, 'leave_management/leave_list.html', context)

@login_required
@hr_or_admin_required
def leave_status_update(request, pk, status=None):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    old_status = leave.status

    if request.method == 'POST':
        status = request.POST.get('status', status or 'Approved')
        classification = request.POST.get('classification', 'Paid Casual Leave')
        rejection_reason = request.POST.get('rejection_reason', '').strip()
    else:
        status = status or request.GET.get('status', 'Approved')
        classification = request.GET.get('classification', 'Paid Casual Leave')
        rejection_reason = request.GET.get('rejection_reason', '').strip()

    if status in ('Approved', 'Rejected'):
        if status == 'Approved':
            if leave.leave_type in ('Permission (Up to 2 Hours)', 'Permission') or classification == 'Approved Permission':
                leave.is_paid = True
                leave.approval_type = 'Approved Permission'
                leave.status = 'Approved'
                leave.reviewed_by = request.user
                leave.save()

                # Parse duration in minutes from leave reason
                dur_hm = re.search(r'\((\d+)h\s*(\d*)m?\)', leave.reason)
                dur_match = re.search(r'\((\d+)\s*mins?\)', leave.reason)
                if dur_hm:
                    h_val = int(dur_hm.group(1))
                    m_val = int(dur_hm.group(2)) if dur_hm.group(2) else 0
                    dur_in_mins = h_val * 60 + m_val
                elif dur_match:
                    dur_in_mins = int(dur_match.group(1))
                else:
                    dur_in_mins = 120
                perm_hrs = Decimal(str(round(dur_in_mins / 60.0, 2)))

                # Deduct from MonthlyPermissionBalance upon fresh approval
                if old_status != 'Approved':
                    month_bal = get_or_create_monthly_permission_balance(leave.employee, leave.from_date.year, leave.from_date.month)
                    month_bal.used_hours = min(month_bal.total_hours_allowed, month_bal.used_hours + perm_hrs)
                    month_bal.used_requests_count = min(month_bal.total_requests_allowed, month_bal.used_requests_count + 1)
                    month_bal.save()

                att, created = Attendance.objects.get_or_create(employee=leave.employee, date=leave.from_date)
                att.is_permission = True
                att.permission_hours = Decimal('2.00')
                att.updated_by = request.user
                att.update_source = 'HR Approved Permission'
                att.leave_reason = leave.reason
                
                # Recompute status with permission:
                effective_mins = att.total_work_minutes + int(att.permission_hours * 60)
                if effective_mins >= 540:
                    att.status = 'Present'
                elif effective_mins >= 270:
                    att.status = 'Half Day'
                elif att.total_work_minutes > 0:
                    att.status = 'Permission - 2 Hours'
                else:
                    att.status = 'Permission - 2 Hours'
                att.save()

                AttendanceAuditLog.objects.create(
                    attendance=att,
                    changed_by=request.user,
                    action='PERMISSION_APPROVED',
                    old_values=f"Status: {old_status}",
                    new_values=f"Approved Permission: {att.permission_hours}h, Attendance Status: {att.status}",
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                messages.success(request, f"Permission request for {leave.employee.display_name()} ({perm_hrs}h) approved successfully. Monthly permission balance updated.")
                HRNotification.objects.filter(leave_request=leave).update(is_read=True)
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            # Check classification: Paid Sick Leave vs Paid Casual Leave
            if classification == 'Paid Sick Leave' or leave.leave_type == 'Sick Leave':
                leave.is_paid = True
                leave.approval_type = 'Paid Sick Leave'
                leave.leave_type = 'Sick Leave'
                att_leave_type = 'Paid Sick Leave'
            elif classification == 'Unpaid Leave':
                # Legacy compatibility
                leave.is_paid = False
                leave.approval_type = 'Unpaid Leave'
                leave.leave_type = 'Unpaid Leave'
                att_leave_type = 'Unpaid Leave'
            else:
                # Paid Casual Leave
                if old_status != 'Approved':
                    leave.employee.casual_leave_balance = max(0, leave.employee.casual_leave_balance - leave.total_days)
                    leave.employee.save(update_fields=['casual_leave_balance'])
                leave.is_paid = True
                leave.approval_type = 'Paid Casual Leave'
                leave.leave_type = 'Casual Leave'
                att_leave_type = 'Paid Casual Leave'

            leave.status = 'Approved'
            leave.reviewed_by = request.user
            leave.save()

            # Synchronize Attendance records for dates in range
            curr = leave.from_date
            while curr <= leave.to_date:
                att, created = Attendance.objects.get_or_create(employee=leave.employee, date=curr)
                # Only mark On Leave if employee hasn't completed actual work on this day
                if att.total_work_minutes < 270:
                    att.status = 'On Leave'
                    att.is_approved_leave = True
                    att.leave_type = att_leave_type
                    att.leave_reason = leave.reason
                    att.updated_by = request.user
                    att.update_source = f'HR Review ({leave.approval_type})'
                    att.save()

                    AttendanceAuditLog.objects.create(
                        attendance=att,
                        changed_by=request.user,
                        action='LEAVE_APPROVED',
                        old_values=old_status,
                        new_values=f"Approved as {leave.approval_type}, Paid: {leave.is_paid}",
                        ip_address=request.META.get('REMOTE_ADDR', '')
                    )
                curr += timedelta(days=1)

            messages.success(
                request,
                f"Leave request for {leave.employee.display_name()} approved as {leave.approval_type}."
            )

        elif status == 'Rejected':
            if leave.leave_type in ('Permission (Up to 2 Hours)', 'Permission'):
                leave.status = 'Rejected'
                leave.reviewed_by = request.user
                leave.rejection_reason = rejection_reason or 'Permission request rejected by HR.'
                leave.save()

                # Revert monthly permission balance if previously approved
                if old_status == 'Approved':
                    dur_hm = re.search(r'\((\d+)h\s*(\d*)m?\)', leave.reason)
                    dur_match = re.search(r'\((\d+)\s*mins?\)', leave.reason)
                    if dur_hm:
                        h_val = int(dur_hm.group(1))
                        m_val = int(dur_hm.group(2)) if dur_hm.group(2) else 0
                        dur_in_mins = h_val * 60 + m_val
                    elif dur_match:
                        dur_in_mins = int(dur_match.group(1))
                    else:
                        dur_in_mins = 120
                    perm_hrs = Decimal(str(round(dur_in_mins / 60.0, 2)))

                    month_bal = get_or_create_monthly_permission_balance(leave.employee, leave.from_date.year, leave.from_date.month)
                    month_bal.used_hours = max(Decimal('0.00'), month_bal.used_hours - perm_hrs)
                    month_bal.used_requests_count = max(0, month_bal.used_requests_count - 1)
                    month_bal.save()

                att = Attendance.objects.filter(employee=leave.employee, date=leave.from_date).first()
                if att and att.is_permission:
                    att.is_permission = False
                    att.permission_hours = Decimal('0.00')
                    if att.in_time and att.out_time:
                        if att.total_work_minutes >= 540:
                            att.status = 'Present'
                        elif att.total_work_minutes >= 270:
                            att.status = 'Half Day'
                        else:
                            att.status = 'Absent'
                    elif att.in_time:
                        att.status = 'Missing Punch-Out'
                    else:
                        att.status = 'Absent'
                    att.updated_by = request.user
                    att.save()

                messages.warning(request, f"Permission request for {leave.employee.display_name()} has been rejected.")
                HRNotification.objects.filter(leave_request=leave).update(is_read=True)
                return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')

            # Revert balance if previously approved as Paid Casual Leave
            if old_status == 'Approved' and leave.is_paid and ('Casual' in leave.approval_type or 'Casual' in leave.leave_type):
                leave.employee.casual_leave_balance = min(1, leave.employee.casual_leave_balance + leave.total_days)
                leave.employee.save(update_fields=['casual_leave_balance'])

            leave.status = 'Rejected'
            leave.reviewed_by = request.user
            leave.rejection_reason = rejection_reason or 'Leave request rejected by HR reviewer.'
            leave.save()

            # Revert attendance records for these dates
            curr = leave.from_date
            while curr <= leave.to_date:
                att = Attendance.objects.filter(employee=leave.employee, date=curr).first()
                if att and att.status == 'On Leave':
                    att.is_approved_leave = False
                    att.leave_type = ''
                    att.leave_reason = f"Rejected: {leave.rejection_reason}"
                    att.status = 'Absent' if not att.in_time else att.status
                    att.updated_by = request.user
                    att.save()
                curr += timedelta(days=1)

            messages.warning(
                request,
                f"Leave request for {leave.employee.display_name()} has been rejected. Calendar marked in red."
            )

        # Mark all notifications for this request as read
        HRNotification.objects.filter(leave_request=leave).update(is_read=True)

    return redirect(request.META.get('HTTP_REFERER') or 'leave_management:list')
