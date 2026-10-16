import calendar
from decimal import Decimal
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.users.decorators import hr_or_admin_required
from apps.employees.models import Employee
from apps.attendance.models import Attendance
from apps.leave_management.models import LeaveRequest
from .models import SalaryStructure, PayrollRecord
from .forms import SalaryStructureForm, GeneratePayrollForm

def calculate_payroll_for_employee(emp, year, month):
    """
    Implements mandatory attendance-based salary calculations:
    1. 9 working hours (>= 540m) count as a full working day -> Full-day salary (no deduction).
    2. 4 hours and 30 minutes (>= 270m and < 540m) count as a half working day -> Half-day salary (0.5 day deducted).
    3. Up to 2 hours of approved permission -> Must not affect salary (no deduction).
    4. Approved leave days -> Must not result in salary deductions (no deduction).
    5. Unexcused absence -> 1.0 day deducted.
    """
    days_in_month = calendar.monthrange(year, month)[1]
    structure = getattr(emp, 'salary_structure', None)

    if structure:
        basic = structure.basic_salary
        hra = structure.hra
        allowances = structure.allowances
        gross_salary = structure.total_earnings
        statutory_deductions = structure.total_deductions
    else:
        basic = emp.basic_salary
        hra = Decimal('0.00')
        allowances = Decimal('0.00')
        gross_salary = basic
        statutory_deductions = Decimal('0.00')

    daily_rate = (gross_salary / Decimal(str(days_in_month))).quantize(Decimal('0.01'))

    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    # 1. Collect approved leave days in this month
    approved_leaves = LeaveRequest.objects.filter(
        employee=emp, status='Approved',
        from_date__lte=month_end, to_date__gte=month_start
    )
    paid_leave_days = set()
    unpaid_leave_days = set()

    for l in approved_leaves:
        if l.leave_type in ('Permission', 'Permission (Up to 2 Hours)') or 'Permission' in l.approval_type:
            continue
        curr = max(l.from_date, month_start)
        end = min(l.to_date, month_end)
        while curr <= end:
            if not l.is_paid or l.approval_type == 'Unpaid Leave' or l.leave_type == 'Unpaid Leave':
                unpaid_leave_days.add(curr.day)
            else:
                paid_leave_days.add(curr.day)
            curr += timedelta(days=1)

    # Include Office-wide Paid Leaves (Full Pay, zero deduction)
    from apps.leave_management.models import OfficePaidLeave
    for opl in OfficePaidLeave.objects.filter(date__year=year, date__month=month):
        paid_leave_days.add(opl.date.day)

    # Exclude attendances and absence evaluations prior to employee joining date
    joining_date = getattr(emp, 'joining_date', None)
    if joining_date:
        earliest_att = Attendance.objects.filter(employee=emp).order_by('date').values_list('date', flat=True).first()
        if earliest_att and earliest_att < joining_date:
            joining_date = earliest_att

    # 2. Inspect attendances in this month (strictly starting from joining date)
    attendances_qs = Attendance.objects.filter(
        employee=emp, date__year=year, date__month=month
    )

    if joining_date and joining_date > month_end and not attendances_qs.exists():
        return {
            'basic_salary': Decimal('0.00'),
            'allowances': Decimal('0.00'),
            'deductions': Decimal('0.00'),
            'net_salary': Decimal('0.00'),
            'remarks': f"Employee official joining date ({joining_date.strftime('%b %d, %Y')}) is after this billing period.",
            'full_days': 0,
            'half_days': 0,
            'permission_days': 0,
            'approved_leaves': 0,
            'unpaid_leaves': 0,
            'absent_days': 0,
            'incomplete_punch_days': [],
        }

    pre_joining_days = 0
    if joining_date and joining_date > month_start:
        pre_joining_days = (joining_date - month_start).days

    if joining_date:
        attendances_qs = attendances_qs.filter(date__gte=joining_date)

    full_days = 0
    half_days = 0
    permission_days = 0
    absent_days = 0
    paid_leave_count = 0
    unpaid_leave_count = 0
    seen_attendance_days = set()

    recorded_absent_days = set()
    incomplete_punch_days = []
    for a in attendances_qs:
        d = a.date.day
        seen_attendance_days.add(d)

        # Official duty counts as full day Present with full pay
        if getattr(a, 'is_official_duty', False) or a.update_source == 'Official Office Duty' or a.leave_type == 'Official Duty':
            full_days += 1
            continue

        # Incomplete attendance: punch-in is recorded but punch-out is missing
        if getattr(a, 'is_missing_punch_out', False) or (a.in_time and not a.out_time):
            incomplete_punch_days.append(d)
            recorded_absent_days.add(d)
            continue

        # If day is in leave and employee did not perform actual work
        if d in paid_leave_days and (not a.in_time and a.total_work_minutes < 270):
            paid_leave_count += 1
            continue
        elif d in unpaid_leave_days and (not a.in_time and a.total_work_minutes < 270):
            unpaid_leave_count += 1
            recorded_absent_days.add(d)
            continue

        if a.status == 'Permission - 2 Hours' or a.is_permission:
            # Approved 2-hour permission -> zero deduction
            permission_days += 1
        elif a.status in ('On Leave', 'Office Holiday') or a.leave_type == 'Paid Leave for the Office':
            if a.leave_type == 'Unpaid Leave' or a.status == 'Leave Without Pay (LWP)':
                unpaid_leave_count += 1
                recorded_absent_days.add(d)
            else:
                paid_leave_count += 1
        elif a.status == 'Present' or a.total_work_minutes >= 540:
            # 9 working hours -> full working day, full-day salary (only if punch-out is present)
            if a.out_time:
                full_days += 1
            else:
                incomplete_punch_days.append(d)
                recorded_absent_days.add(d)
        elif a.status == 'Half Day' or (270 <= a.total_work_minutes < 540):
            # 4h 30m -> half working day, half-day salary (only if punch-out is present)
            if a.out_time:
                half_days += 1
            else:
                incomplete_punch_days.append(d)
                recorded_absent_days.add(d)
        elif a.status in ('Absent', 'Missed Punch-In', 'Leave Without Pay (LWP)'):
            absent_days += 1
            recorded_absent_days.add(d)

    # Check Sunday sandwich continuous absence rule (up to 5 days continuous absence encompassing Sunday)
    sandwich_sunday_count = 0
    for day_num in range(1, days_in_month + 1):
        cur_d = date(year, month, day_num)
        if joining_date and cur_d < joining_date:
            continue
        if cur_d.weekday() == 6:  # Sunday
            # Check continuous absence immediately preceding and succeeding
            sat_absent = (day_num - 1) in recorded_absent_days
            mon_absent = (day_num + 1) in recorded_absent_days
            if sat_absent and mon_absent:
                sandwich_sunday_count += 1

    # Add any approved leaves that didn't have an Attendance record row yet (strictly after joining)
    filtered_paid_leave_days = {d for d in paid_leave_days if not (joining_date and date(year, month, d) < joining_date)}
    filtered_unpaid_leave_days = {d for d in unpaid_leave_days if not (joining_date and date(year, month, d) < joining_date)}
    unlinked_paid = len(filtered_paid_leave_days - seen_attendance_days)
    unlinked_unpaid = len(filtered_unpaid_leave_days - seen_attendance_days)
    total_paid_leaves = paid_leave_count + unlinked_paid
    total_unpaid_leaves = unpaid_leave_count + unlinked_unpaid + sandwich_sunday_count

    # Uncorrected missing punch-outs default to Leave Without Pay (LWP) per policy
    unique_incomplete_days = sorted(list(set(incomplete_punch_days)))
    total_unpaid_leaves += len(unique_incomplete_days)

    half_day_deduction = (Decimal(str(half_days)) * Decimal('0.5') * daily_rate).quantize(Decimal('0.01'))
    absent_deduction = (Decimal(str(absent_days)) * daily_rate).quantize(Decimal('0.01'))
    unpaid_leave_deduction = (Decimal(str(total_unpaid_leaves)) * daily_rate).quantize(Decimal('0.01'))

    attendance_deductions = half_day_deduction + absent_deduction + unpaid_leave_deduction
    total_deductions = statutory_deductions + attendance_deductions
    net_salary = max(Decimal('0.00'), gross_salary - total_deductions)

    remarks = (
        f"Attended: Full Days (9h+): {full_days}, "
        f"Half Days (4.5h+): {half_days} (-₹{half_day_deduction:.2f}), "
        f"Permission (Up to 2h): {permission_days} (Full Pay), "
        f"Paid Leaves, Sundays & Office Holidays: {total_paid_leaves} (Full Pay), "
        f"Unpaid Leaves / Sandwich / LWP: {total_unpaid_leaves} (-₹{unpaid_leave_deduction:.2f}), "
        f"Absents/Missed Punch-In: {absent_days} (-₹{absent_deduction:.2f})."
    )
    if pre_joining_days > 0:
        remarks += f" [Pre-Joining Period: {pre_joining_days} day(s) prior to {joining_date.strftime('%b %d, %Y')} excluded from absenteeism and deductions]."
    if sandwich_sunday_count > 0:
        remarks += f" [Sandwich/Continuous Absence: {sandwich_sunday_count} Sunday(s) converted to LWP per policy]."
    if unique_incomplete_days:
        remarks += (
            f" [NOTICE: Incomplete attendance (missing punch-out) on day(s) {unique_incomplete_days}. "
            f"Working hours and salary were NOT finalized for these days. By policy, uncorrected incomplete punches are treated as Leave Without Pay (LWP) until an authorized HR staff member verifies and enters the manual punch-out correction. Please contact HR to enter or correct missing punch-out time manually.]"
        )

    return {
        'basic_salary': basic,
        'allowances': hra + allowances,
        'deductions': total_deductions,
        'net_salary': net_salary,
        'remarks': remarks,
        'full_days': full_days,
        'half_days': half_days,
        'permission_days': permission_days,
        'approved_leaves': total_paid_leaves,
        'unpaid_leaves': total_unpaid_leaves,
        'absent_days': absent_days,
        'incomplete_punch_days': unique_incomplete_days,
    }

@login_required
def payroll_list(request):
    profile = getattr(request.user, 'employee', None)
    is_management = profile and profile.role in ('ADMIN', 'HR')

    selected_year = int(request.GET.get('year', date.today().year))
    selected_month = int(request.GET.get('month', date.today().month))

    if is_management:
        records = PayrollRecord.objects.select_related(
            'employee', 'employee__user', 'employee__department'
        ).filter(year=selected_year, month=selected_month)
    else:
        records = PayrollRecord.objects.filter(employee=profile)

    generate_form = GeneratePayrollForm(initial={'year': selected_year, 'month': selected_month})

    total_disbursed = sum(r.net_salary for r in records if r.status == 'Paid')
    total_pending = sum(r.net_salary for r in records if r.status != 'Paid')

    context = {
        'records': records,
        'is_management': is_management,
        'generate_form': generate_form,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'total_disbursed': total_disbursed,
        'total_pending': total_pending,
    }
    return render(request, 'payroll/payroll_list.html', context)

@login_required
@hr_or_admin_required
def generate_payroll(request):
    if request.method == 'POST':
        form = GeneratePayrollForm(request.POST)
        if form.is_valid():
            year = int(form.cleaned_data['year'])
            month = int(form.cleaned_data['month'])

            active_employees = Employee.objects.filter(is_active_employee=True)
            created_count = 0

            for emp in active_employees:
                calc = calculate_payroll_for_employee(emp, year, month)

                record, created = PayrollRecord.objects.update_or_create(
                    employee=emp,
                    year=year,
                    month=month,
                    defaults={
                        'basic_salary': calc['basic_salary'],
                        'allowances': calc['allowances'],
                        'deductions': calc['deductions'],
                        'net_salary': calc['net_salary'],
                        'remarks': calc['remarks'],
                    }
                )
                if created:
                    created_count += 1

            messages.success(request, f"Payroll processed for {month}/{year}. Attendance rules applied: 9h Full Day, 4.5h Half Day, 2h Permission (0 deduction), Approved Leaves (0 deduction).")
            return redirect(f"/payroll/?year={year}&month={month}")
    return redirect('payroll:list')

@login_required
def payslip_detail(request, pk):
    record = get_object_or_404(
        PayrollRecord.objects.select_related('employee', 'employee__user', 'employee__department', 'employee__designation'),
        pk=pk
    )
    profile = getattr(request.user, 'employee', None)
    if profile != record.employee and (not profile or profile.role not in ('ADMIN', 'HR')):
        messages.error(request, "Permission denied to view this payslip.")
        return redirect('payroll:list')

    month_name = date(2000, record.month, 1).strftime('%B')
    return render(request, 'payroll/payslip.html', {
        'record': record,
        'month_name': month_name,
    })

@login_required
@hr_or_admin_required
def mark_paid(request, pk):
    record = get_object_or_404(PayrollRecord, pk=pk)
    record.status = 'Paid'
    record.payment_date = date.today()
    record.save(update_fields=['status', 'payment_date'])
    messages.success(request, f"Payroll for {record.employee.display_name()} ({record.month}/{record.year}) marked as Paid.")
    return redirect(f"/payroll/?year={record.year}&month={record.month}")
