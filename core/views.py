import calendar
import csv
from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from .models import EmployeeProfile, MonthlyLeaveCredit, Attendance, DailyWork, LeaveRequest
from .forms import DailyWorkForm, LeaveRequestForm, EmployeeCreateForm, AttendanceUpdateForm, PunchMachineUploadForm


def front_page(request):
    return render(request, 'core/front_page.html')


def get_profile(user):
    try:
        return EmployeeProfile.objects.get(user=user)
    except EmployeeProfile.DoesNotExist:
        role = 'ADMIN' if (user.is_superuser or user.is_staff) else 'EMPLOYEE'
        code = f"{'ADM' if role == 'ADMIN' else 'EMP'}{user.id:04d}"
        idx = 1
        while EmployeeProfile.objects.filter(employee_code=code).exists():
            code = f"{'ADM' if role == 'ADMIN' else 'EMP'}{user.id:04d}_{idx}"
            idx += 1
        return EmployeeProfile.objects.create(
            user=user,
            employee_code=code,
            role=role,
            department='Administration' if role == 'ADMIN' else 'General',
            designation='Administrator' if role == 'ADMIN' else 'Staff',
            casual_leave_balance=1,
        )


def add_monthly_casual_leave(profile):
    today = timezone.localdate()
    credit, created = MonthlyLeaveCredit.objects.get_or_create(
        employee=profile,
        year=today.year,
        month=today.month,
        defaults={'casual_added': 1}
    )
    if created:
        profile.casual_leave_balance += 1
        profile.save()
    return created


def month_prev_next(year, month):
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    return prev_year, prev_month, next_year, next_month


def build_calendar(profile, year=None, month=None):
    today = timezone.localdate()
    try:
        year = int(year) if year else today.year
        month = int(month) if month else today.month
        if month < 1 or month > 12:
            year, month = today.year, today.month
    except (ValueError, TypeError):
        year, month = today.year, today.month

    month_days = calendar.monthcalendar(year, month)

    working_dates = set(
        Attendance.objects.filter(
            employee=profile,
            date__year=year,
            date__month=month,
            in_time__isnull=False
        ).values_list('date__day', flat=True)
    )

    leave_dates = set()
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    leaves = LeaveRequest.objects.filter(
        employee=profile,
        status='Approved',
        from_date__lte=month_end,
        to_date__gte=month_start
    )

    for leave in leaves:
        current = max(leave.from_date, month_start)
        end = min(leave.to_date, month_end)
        while current <= end:
            leave_dates.add(current.day)
            current += timedelta(days=1)

    rows = []
    for week in month_days:
        row = []
        for day in week:
            if day == 0:
                row.append({'day': '', 'class_name': 'empty-day'})
            elif day in leave_dates:
                row.append({'day': day, 'class_name': 'leave-day'})
            elif day in working_dates:
                row.append({'day': day, 'class_name': 'working-day'})
            else:
                row.append({'day': day, 'class_name': ''})
        rows.append(row)

    prev_year, prev_month, next_year, next_month = month_prev_next(year, month)
    return {
        'calendar_rows': rows,
        'month_name': calendar.month_name[month],
        'current_year': year,
        'current_month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
    }


def check_leave_balance(profile, leave_type, days):
    if leave_type == 'Casual Leave':
        return profile.casual_leave_balance >= days
    return False


def deduct_leave_balance(profile, leave_type, days):
    if leave_type == 'Casual Leave':
        profile.casual_leave_balance = max(0, profile.casual_leave_balance - days)
    profile.save()


def is_hr_or_admin(profile):
    return profile.role in ['HR', 'ADMIN']


@login_required
def dashboard(request):
    profile = get_profile(request.user)
    add_monthly_casual_leave(profile)

    if profile.role == 'ADMIN':
        return redirect('admin_dashboard')
    if profile.role == 'HR':
        return redirect('hr_dashboard')
    return redirect('employee_dashboard')


@login_required
def employee_dashboard(request):
    profile = get_profile(request.user)
    add_monthly_casual_leave(profile)

    today = timezone.localdate()
    now = timezone.localtime()
    attendance, created = Attendance.objects.get_or_create(employee=profile, date=today)

    year = request.GET.get('year', today.year)
    month = request.GET.get('month', today.month)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'punch_in':
            if attendance.in_time:
                messages.warning(request, 'Already punched in today.')
            else:
                attendance.in_time = now.time()
                attendance.updated_by = request.user
                attendance.update_source = 'Employee Punch'
                attendance.save()
                messages.success(request, 'Punch In auto updated successfully.')
            return redirect('employee_dashboard')

        if action == 'punch_out':
            if not attendance.in_time:
                messages.error(request, 'Please punch in first.')
            elif attendance.out_time:
                messages.warning(request, 'Already punched out today.')
            else:
                attendance.out_time = now.time()
                attendance.updated_by = request.user
                attendance.update_source = 'Employee Punch'
                attendance.save()
                messages.success(request, 'Punch Out auto updated successfully.')
            return redirect('employee_dashboard')

        if action == 'daily_work':
            work_form = DailyWorkForm(request.POST)
            if work_form.is_valid():
                work = work_form.save(commit=False)
                work.employee = profile
                work.date = today
                work.save()
                messages.success(request, 'Daily work updated successfully.')
            else:
                for err in work_form.errors.values():
                    messages.error(request, err.as_text())
            return redirect('employee_dashboard')

        if action == 'leave_request':
            leave_form = LeaveRequestForm(request.POST)
            if leave_form.is_valid():
                leave = leave_form.save(commit=False)
                leave.employee = profile
                leave.total_days = (leave.to_date - leave.from_date).days + 1

                if not check_leave_balance(profile, leave.leave_type, leave.total_days):
                    messages.error(request, f'Not enough {leave.leave_type} balance.')
                    return redirect('employee_dashboard')

                leave.save()
                messages.success(request, 'Leave request submitted successfully. HR approval pending.')
            else:
                for err in leave_form.errors.values():
                    messages.error(request, err.as_text())
            return redirect('employee_dashboard')

    context = {
        'profile': profile,
        'today': today,
        'attendance': attendance,
        'work_form': DailyWorkForm(),
        'leave_form': LeaveRequestForm(),
        'works': DailyWork.objects.filter(employee=profile)[:8],
        'leaves': LeaveRequest.objects.filter(employee=profile)[:8],
        'attendances': Attendance.objects.filter(employee=profile)[:10],
    }
    context.update(build_calendar(profile, year, month))
    return render(request, 'core/employee_dashboard.html', context)


@login_required
def hr_dashboard(request):
    profile = get_profile(request.user)
    add_monthly_casual_leave(profile)

    if not is_hr_or_admin(profile):
        messages.error(request, 'Only HR or Admin can open HR page.')
        return redirect('employee_dashboard')

    today = timezone.localdate()
    now = timezone.localtime()
    hr_attendance, created = Attendance.objects.get_or_create(employee=profile, date=today)

    attendance_form = AttendanceUpdateForm()
    upload_form = PunchMachineUploadForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'hr_punch_in':
            if hr_attendance.in_time:
                messages.warning(request, 'HR already punched in today.')
            else:
                hr_attendance.in_time = now.time()
                hr_attendance.updated_by = request.user
                hr_attendance.update_source = 'HR Punch'
                hr_attendance.save()
                messages.success(request, 'HR Punch In auto updated successfully.')
            return redirect('hr_dashboard')

        if action == 'hr_punch_out':
            if not hr_attendance.in_time:
                messages.error(request, 'Please punch in first.')
            elif hr_attendance.out_time:
                messages.warning(request, 'HR already punched out today.')
            else:
                hr_attendance.out_time = now.time()
                hr_attendance.updated_by = request.user
                hr_attendance.update_source = 'HR Punch'
                hr_attendance.save()
                messages.success(request, 'HR Punch Out auto updated successfully.')
            return redirect('hr_dashboard')

        if action == 'add_user':
            form = EmployeeCreateForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Employee / HR / Admin user created successfully.')
                return redirect('hr_dashboard')

        if action == 'manual_attendance':
            attendance_form = AttendanceUpdateForm(request.POST)
            if attendance_form.is_valid():
                employee = attendance_form.cleaned_data['employee']
                work_date = attendance_form.cleaned_data['date']
                in_time = attendance_form.cleaned_data['in_time']
                out_time = attendance_form.cleaned_data['out_time']
                att, created = Attendance.objects.get_or_create(employee=employee, date=work_date)
                att.in_time = in_time
                att.out_time = out_time
                att.updated_by = request.user
                att.update_source = 'HR/Admin Manual Update'
                att.save()
                messages.success(request, 'Employee attendance updated by HR/Admin.')
                return redirect('hr_dashboard')

        if action == 'punch_machine_upload':
            upload_form = PunchMachineUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                csv_file = request.FILES['csv_file']
                try:
                    raw_content = csv_file.read()
                    try:
                        decoded = raw_content.decode('utf-8-sig').splitlines()
                    except UnicodeDecodeError:
                        decoded = raw_content.decode('latin-1').splitlines()
                    reader = csv.DictReader(decoded)
                    count = 0
                    for row in reader:
                        cleaned = {k.strip() if k else '': (v.strip() if v else '') for k, v in row.items()}
                        emp_code = cleaned.get('employee_code')
                        raw_date = cleaned.get('date')
                        raw_time = cleaned.get('time')
                        punch_type = cleaned.get('type', '').lower()

                        if not emp_code or not raw_date or not raw_time:
                            continue

                        try:
                            work_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
                            punch_time = datetime.strptime(raw_time, '%H:%M:%S').time()
                        except ValueError:
                            continue

                        try:
                            employee = EmployeeProfile.objects.get(employee_code=emp_code)
                        except EmployeeProfile.DoesNotExist:
                            continue

                        att, created = Attendance.objects.get_or_create(employee=employee, date=work_date)
                        if punch_type == 'in':
                            att.in_time = punch_time
                        elif punch_type == 'out':
                            att.out_time = punch_time
                        att.updated_by = request.user
                        att.update_source = 'Punch Machine CSV'
                        att.save()
                        count += 1

                    messages.success(request, f'Punch machine CSV updated successfully. {count} records imported.')
                except Exception as e:
                    messages.error(request, f'Failed to process CSV file: {e}')
                return redirect('hr_dashboard')
            else:
                for err in upload_form.errors.values():
                    messages.error(request, err.as_text())
                return redirect('hr_dashboard')

    else:
        form = EmployeeCreateForm()

    if request.method != 'POST' or request.POST.get('action') != 'add_user':
        form = EmployeeCreateForm()

    query = request.GET.get('q', '')
    employees = EmployeeProfile.objects.select_related('user').all().order_by('-id')
    if query:
        employees = employees.filter(
            Q(employee_code__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(department__icontains=query) |
            Q(designation__icontains=query) |
            Q(role__icontains=query)
        )

    context = {
        'profile': profile,
        'form': form,
        'attendance_form': attendance_form,
        'upload_form': upload_form,
        'employees': employees,
        'attendance': Attendance.objects.select_related('employee', 'employee__user').all()[:80],
        'works': DailyWork.objects.select_related('employee', 'employee__user').all()[:80],
        'leaves': LeaveRequest.objects.select_related('employee', 'employee__user').all()[:80],
        'pending_leaves': LeaveRequest.objects.filter(status='Pending').count(),
        'hr_attendance': hr_attendance,
        'today': today,
        'query': query,
    }
    return render(request, 'core/hr_dashboard.html', context)


@login_required
def admin_dashboard(request):
    profile = get_profile(request.user)
    add_monthly_casual_leave(profile)

    if profile.role != 'ADMIN':
        messages.error(request, 'Only Admin can open admin page.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = EmployeeCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'New user created successfully.')
            return redirect('admin_dashboard')
    else:
        form = EmployeeCreateForm()

    context = {
        'profile': profile,
        'form': form,
        'employees': EmployeeProfile.objects.select_related('user').all().order_by('-id'),
        'attendance': Attendance.objects.select_related('employee', 'employee__user').all()[:100],
        'works': DailyWork.objects.select_related('employee', 'employee__user').all()[:100],
        'leaves': LeaveRequest.objects.select_related('employee', 'employee__user').all()[:100],
        'total_users': EmployeeProfile.objects.count(),
        'total_attendance': Attendance.objects.count(),
        'total_work': DailyWork.objects.count(),
        'total_leave': LeaveRequest.objects.count(),
    }
    return render(request, 'core/admin_dashboard.html', context)


@login_required
def update_leave_status(request, leave_id, status):
    profile = get_profile(request.user)
    if not is_hr_or_admin(profile):
        messages.error(request, 'Only HR/Admin can approve or reject leave.')
        return redirect('dashboard')

    leave = get_object_or_404(LeaveRequest, id=leave_id)
    old_status = leave.status

    if status in ['Approved', 'Rejected']:
        if status == 'Approved' and old_status != 'Approved':
            if not check_leave_balance(leave.employee, leave.leave_type, leave.total_days):
                messages.error(request, f'{leave.employee.display_name()} has not enough {leave.leave_type} balance.')
                return redirect('hr_dashboard' if profile.role == 'HR' else 'admin_dashboard')
            deduct_leave_balance(leave.employee, leave.leave_type, leave.total_days)

        leave.status = status
        leave.save()
        messages.success(request, f'Leave request {status.lower()} successfully.')

    return redirect('hr_dashboard' if profile.role == 'HR' else 'admin_dashboard')


@login_required
def delete_employee(request, employee_id):
    profile = get_profile(request.user)
    if profile.role != 'ADMIN':
        messages.error(request, 'Only Admin can delete employees.')
        return redirect('dashboard')

    employee = get_object_or_404(EmployeeProfile, id=employee_id)
    if employee.user == request.user:
        messages.error(request, 'You cannot delete your own account.')
    else:
        user = employee.user
        employee.delete()
        user.delete()
        messages.success(request, 'Employee deleted successfully.')
    return redirect('admin_dashboard')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')
