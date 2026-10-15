import base64
from datetime import datetime, date
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.utils import timezone
from apps.users.decorators import hr_or_admin_required
from apps.employees.models import Employee
from .models import Attendance, DailyWork, AttendanceAuditLog, BiometricDevice
from .forms import ManualAttendanceForm, DailyWorkForm, BiometricDeviceForm
from .biometric_service import test_device_connection, sync_biometric_device
from .services import (
    check_and_restore_casual_leave_on_attendance,
    reset_daily_missed_punch_in_status,
    mark_employee_official_duty,
    correct_missing_punch_out,
    mark_office_holiday_calendar,
)


def parse_base64_image(data_uri, name_prefix):
    """Safely decodes HTML5 camera DataURI into a Django ContentFile."""
    if not data_uri or ';base64,' not in data_uri:
        return None
    try:
        header, encoded = data_uri.split(';base64,', 1)
        ext = header.split('/')[-1] if '/' in header else 'jpg'
        if ext == 'jpeg':
            ext = 'jpg'
        decoded = base64.b64decode(encoded)
        filename = f"{name_prefix}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        return ContentFile(decoded, name=filename)
    except Exception:
        return None


@login_required
def punch_view(request):
    """
    Handles employee, HR, and administrator mandatory punch-in and punch-out.
    Enforces valid GPS location access and live selfie capture for every punch.
    If GPS access or selfie capture is unavailable, invalid, or denied, prevents the punch action
    and displays a clear error message explaining that both GPS location and a live selfie are mandatory.
    Prevents duplicate punch-in and punch-out submissions.
    """
    profile = getattr(request.user, 'employee', None)
    if not profile:
        messages.error(request, "Employee profile required to punch.")
        return redirect('dashboard:index')

    reset_daily_missed_punch_in_status()
    today = timezone.localdate()
    now_time = timezone.localtime().time()
    attendance, _ = Attendance.objects.get_or_create(employee=profile, date=today)

    action = request.POST.get('action')
    photo_data = request.POST.get('photo_data', '')
    lat_val = request.POST.get('latitude', '').strip()
    lon_val = request.POST.get('longitude', '').strip()
    loc_desc = request.POST.get('location', '').strip()

    latitude = None
    longitude = None
    if lat_val and lon_val:
        try:
            latitude = Decimal(str(float(lat_val)))
            longitude = Decimal(str(float(lon_val)))
        except (ValueError, TypeError):
            latitude = None
            longitude = None

    client_ip = request.META.get('REMOTE_ADDR', '')

    if action == 'punch_in':
        # Prevent duplicate punch-in
        if attendance.in_time:
            messages.error(request, "You have already punched in for today.")
            return redirect('dashboard:index')

        # Strictly enforce mandatory GPS coordinates and live selfie capture
        if not photo_data or not parse_base64_image(photo_data, f"in_{profile.employee_code}"):
            messages.error(request, "Both GPS location and a live selfie are mandatory. Live selfie capture is unavailable, invalid, or was not provided.")
            return redirect('dashboard:index')

        if latitude is None or longitude is None:
            messages.error(request, "Both GPS location and a live selfie are mandatory. Valid GPS location access was not provided or was denied.")
            return redirect('dashboard:index')

        photo_file = parse_base64_image(photo_data, f"in_{profile.employee_code}")
        old_val = f"in: None, out: {attendance.out_time}"
        attendance.in_time = now_time
        attendance.status = 'Missing Punch-Out'
        attendance.update_source = f"{profile.role} Punch (GPS/Selfie)"
        attendance.in_photo = photo_file
        attendance.in_latitude = latitude
        attendance.in_longitude = longitude
        attendance.in_location = loc_desc or f"GPS: {latitude}, {longitude}"
        attendance.save()

        # Record audit log
        AttendanceAuditLog.objects.create(
            attendance=attendance,
            changed_by=request.user,
            action='PUNCH_IN',
            old_values=old_val,
            new_values=f"Time: {now_time}, GPS: ({latitude}, {longitude}), Location: {attendance.in_location}, Selfie: Verified",
            ip_address=client_ip
        )
        messages.success(request, f"Punch In recorded at {now_time.strftime('%I:%M %p')} with verified live selfie and GPS location.")

    elif action == 'punch_out':
        # Validate that punch-in exists and punch-out has not already occurred
        if not attendance.in_time:
            messages.error(request, "Please punch in before recording punch out.")
            return redirect('dashboard:index')

        if attendance.out_time:
            messages.error(request, "You have already punched out for today.")
            return redirect('dashboard:index')

        # Strictly enforce mandatory GPS coordinates and live selfie capture
        if not photo_data or not parse_base64_image(photo_data, f"out_{profile.employee_code}"):
            messages.error(request, "Both GPS location and a live selfie are mandatory. Live selfie capture is unavailable, invalid, or was not provided.")
            return redirect('dashboard:index')

        if latitude is None or longitude is None:
            messages.error(request, "Both GPS location and a live selfie are mandatory. Valid GPS location access was not provided or was denied.")
            return redirect('dashboard:index')

        photo_file = parse_base64_image(photo_data, f"out_{profile.employee_code}")
        old_val = f"in: {attendance.in_time}, out: None"
        attendance.out_time = now_time
        attendance.update_source = f"{profile.role} Punch (GPS/Selfie)"
        attendance.out_photo = photo_file
        attendance.out_latitude = latitude
        attendance.out_longitude = longitude
        attendance.out_location = loc_desc or f"GPS: {latitude}, {longitude}"
        attendance.save()

        # Record audit log
        AttendanceAuditLog.objects.create(
            attendance=attendance,
            changed_by=request.user,
            action='PUNCH_OUT',
            old_values=old_val,
            new_values=f"Time: {now_time}, GPS: ({latitude}, {longitude}), Duration: {attendance.total_work_time}, Selfie: Verified",
            ip_address=client_ip
        )
        messages.success(request, f"Punch Out recorded at {now_time.strftime('%I:%M %p')}. Total: {attendance.total_work_time}")

        # Automatic Casual Leave restoration if employee applied for leave but attended office
        restored, msg = check_and_restore_casual_leave_on_attendance(profile, today, attendance, changed_by=request.user)
        if restored:
            messages.info(request, f"Notice: Casual leave for today was automatically cancelled because you attended office and completed {attendance.total_work_time}. 1 day has been restored to your Casual Leave balance! (New Balance: {profile.casual_leave_balance})")

    return redirect('dashboard:index')


@login_required
@hr_or_admin_required
def correct_punch_out(request):
    """
    Dedicated view allowing authorized HR staff and Administrators to manually enter
    or correct missing punch-out times for employees who punched in but missed punch-out.
    Enforces audit logging with HR user ID, timestamp, original and updated details, and reason.
    Strictly restricted from regular employees. No GPS/selfie required for historical HR corrections.
    """
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        date_str = request.POST.get('date')
        out_time_str = request.POST.get('out_time')
        reason = request.POST.get('reason', '').strip()

        if not emp_id or not date_str or not out_time_str or not reason:
            messages.error(request, "Employee, Date, Verified Punch-Out Time, and Correction Reason are all required.")
            return redirect(request.META.get('HTTP_REFERER') or 'dashboard:index')

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format. Expected YYYY-MM-DD.")
            return redirect(request.META.get('HTTP_REFERER') or 'dashboard:index')

        try:
            time_parts = [int(p) for p in out_time_str.split(':')]
            from datetime import time as dt_time
            if len(time_parts) >= 2:
                verified_time = dt_time(time_parts[0], time_parts[1])
            else:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, "Invalid time format. Expected HH:MM (e.g. 18:00).")
            return redirect(request.META.get('HTTP_REFERER') or 'dashboard:index')

        employee = get_object_or_404(Employee, id=emp_id)
        client_ip = request.META.get('REMOTE_ADDR', '')
        success, msg = correct_missing_punch_out(
            employee=employee,
            att_date=target_date,
            verified_out_time=verified_time,
            reason=reason,
            hr_user=request.user,
            ip_address=client_ip
        )
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)

    return redirect(request.META.get('HTTP_REFERER') or 'dashboard:index')


@login_required
@hr_or_admin_required
def attendance_list(request):
    reset_daily_missed_punch_in_status()
    date_filter = request.GET.get('date', '')
    employee_code = request.GET.get('employee_code', '').strip()

    records = Attendance.objects.select_related('employee', 'employee__user', 'employee__department').all()

    if date_filter:
        records = records.filter(date=date_filter)
    if employee_code:
        records = records.filter(employee__employee_code__icontains=employee_code)

    manual_form = ManualAttendanceForm()
    device_form = BiometricDeviceForm()
    devices = BiometricDevice.objects.all()

    context = {
        'attendances': records,  # Passed for CSS scroll container
        'date_filter': date_filter,
        'employee_code': employee_code,
        'manual_form': manual_form,
        'device_form': device_form,
        'devices': devices,
        'total_count': records.count(),
    }
    return render(request, 'attendance/attendance_list.html', context)


@login_required
@hr_or_admin_required
def manual_update(request):
    """Allows authorized Admin and HR users to manually add or correct attendance with full audit logs."""
    if request.method == 'POST':
        form = ManualAttendanceForm(request.POST)
        if form.is_valid():
            emp = form.cleaned_data['employee']
            att_date = form.cleaned_data['date']
            att, created = Attendance.objects.get_or_create(employee=emp, date=att_date)

            old_val = f"in: {att.in_time}, out: {att.out_time}, status: {att.status}"
            att.in_time = form.cleaned_data['in_time']
            att.out_time = form.cleaned_data['out_time']
            att.status = form.cleaned_data['status']
            att.leave_type = form.cleaned_data.get('leave_type', '')
            att.leave_reason = form.cleaned_data.get('leave_reason', '')
            if att.status == 'Permission - 2 Hours':
                att.is_permission = True
                att.permission_hours = Decimal('2.00')
            elif att.status == 'On Leave':
                att.is_approved_leave = True

            att.updated_by = request.user
            att.update_source = 'HR/Admin Manual Update'
            att.save()

            # Record audit log
            AttendanceAuditLog.objects.create(
                attendance=att,
                changed_by=request.user,
                action='MANUAL_UPDATE' if not created else 'MANUAL_CREATE',
                old_values=old_val if not created else 'NEW_RECORD',
                new_values=f"in: {att.in_time}, out: {att.out_time}, status: {att.status}, type: {att.leave_type}",
                ip_address=request.META.get('REMOTE_ADDR', '')
            )

            # Automatic Casual Leave restoration if employee attended office
            restored, msg = check_and_restore_casual_leave_on_attendance(emp, att_date, att, changed_by=request.user)
            if restored:
                messages.info(request, f"Notice: Casual leave for {emp.display_name()} on {att_date} was cancelled and +1 day restored to balance due to recorded office attendance ({att.total_work_time}).")

            messages.success(request, f"Attendance record for {emp.display_name()} ({att_date}) updated with audit trail.")
            return redirect(request.META.get('HTTP_REFERER') or 'attendance:list')
        else:
            for err_list in form.errors.values():
                for err in err_list:
                    messages.error(request, err)
    return redirect('attendance:list')


@login_required
@hr_or_admin_required
def mark_official_duty(request):
    """
    Allows authorized HR and Admin users to mark an employee as on official office duty
    or official work assignment for a selected date.
    Automatically marks the employee as Present instead of Leave, restores casual leave balance
    if previously deducted, and synchronizes attendance and payroll calculations with audit logging.
    """
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        date_str = request.POST.get('date')
        duty_title = request.POST.get('duty_title', '').strip() or 'Official Office Duty / Work Assignment'
        notes = request.POST.get('notes', '').strip()

        if not emp_id or not date_str:
            messages.error(request, "Please select both an employee and a date.")
            return redirect(request.META.get('HTTP_REFERER') or 'attendance:list')

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return redirect(request.META.get('HTTP_REFERER') or 'attendance:list')

        target_emp = get_object_or_404(Employee, id=emp_id)
        success, msg = mark_employee_official_duty(
            employee=target_emp,
            att_date=target_date,
            duty_title=duty_title,
            notes=notes,
            marked_by=request.user
        )
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)

    return redirect(request.META.get('HTTP_REFERER') or 'attendance:list')




@login_required
@hr_or_admin_required
def device_manage(request):
    """Allows Admin/HR to register biometric devices or trigger automated sync."""
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_device':
            form = BiometricDeviceForm(request.POST)
            if form.is_valid():
                device = form.save()
                messages.success(request, f"Biometric device '{device.name}' added successfully.")
            else:
                for err_list in form.errors.values():
                    for err in err_list:
                        messages.error(request, err)
        elif action == 'test_device':
            device_id = request.POST.get('device_id')
            device = get_object_or_404(BiometricDevice, id=device_id)
            online, msg = test_device_connection(device)
            if online:
                messages.success(request, f"Biometric Device '{device.name}': {msg}")
            else:
                messages.warning(request, f"Biometric Device '{device.name}': {msg}")
        elif action == 'sync_device':
            device_id = request.POST.get('device_id')
            device = get_object_or_404(BiometricDevice, id=device_id)
            synced, msg = sync_biometric_device(device, user=request.user)
            if synced > 0:
                messages.success(request, msg)
            else:
                messages.info(request, msg)

    return redirect('attendance:list')


@login_required
def daily_work_list(request):
    profile = getattr(request.user, 'employee', None)
    is_management = profile and profile.role in ('ADMIN', 'HR')

    if is_management:
        works = DailyWork.objects.select_related('employee', 'employee__user').all()
    else:
        works = DailyWork.objects.filter(employee=profile)

    form = DailyWorkForm()
    if request.method == 'POST':
        form = DailyWorkForm(request.POST, request.FILES)
        if form.is_valid():
            work = form.save(commit=False)
            work.employee = profile
            work.date = timezone.localdate()
            work.save()
            messages.success(request, "Daily task report with attachment submitted successfully.")
            return redirect('attendance:daily_work')
        else:
            for err_list in form.errors.values():
                for err in err_list:
                    messages.error(request, err)

    context = {
        'works': works,
        'form': form,
        'is_management': is_management,
    }
    return render(request, 'attendance/daily_work_list.html', context)
