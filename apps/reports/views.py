import csv
import io
import os
import zipfile
from datetime import date, timedelta, datetime
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, Image as RLImage
)
from apps.users.decorators import hr_or_admin_required
from apps.employees.models import Employee
from apps.departments.models import Department
from apps.attendance.models import Attendance
from apps.leave_management.models import LeaveRequest
from apps.payroll.models import PayrollRecord

@login_required
@hr_or_admin_required
def reports_index(request):
    total_staff = Employee.objects.filter(is_active_employee=True).count()
    total_records = Attendance.objects.count()
    total_leaves = LeaveRequest.objects.count()
    total_payroll = PayrollRecord.objects.count()

    context = {
        'total_staff': total_staff,
        'total_records': total_records,
        'total_leaves': total_leaves,
        'total_payroll': total_payroll,
    }
    return render(request, 'reports/reports_index.html', context)

@login_required
@hr_or_admin_required
def attendance_report(request):
    start_date = request.GET.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', date.today().strftime('%Y-%m-%d'))
    dept_id = request.GET.get('department', '')
    export = request.GET.get('export', '')

    records = Attendance.objects.select_related('employee', 'employee__user', 'employee__department').filter(
        date__range=[start_date, end_date]
    )
    if dept_id:
        records = records.filter(employee__department_id=dept_id)

    if export == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_report_{start_date}_to_{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Employee Code', 'Name', 'Department', 'Date', 'In Time', 'Out Time', 'Duration', 'Source', 'Status'])
        for r in records:
            writer.writerow([
                r.employee.employee_code,
                r.employee.display_name(),
                r.employee.department.name if r.employee.department else 'N/A',
                r.date,
                r.in_time or '-',
                r.out_time or '-',
                r.total_work_time,
                r.update_source,
                r.status,
            ])
        return response

    context = {
        'records': records[:200],
        'start_date': start_date,
        'end_date': end_date,
        'dept_id': dept_id,
        'departments': Department.objects.all(),
        'total_count': records.count(),
    }
    return render(request, 'reports/attendance_report.html', context)

@login_required
@hr_or_admin_required
def leave_report(request):
    year = int(request.GET.get('year', date.today().year))
    leaves = LeaveRequest.objects.select_related('employee', 'employee__user', 'employee__department').filter(
        from_date__year=year
    )

    stats = leaves.values('status').annotate(count=Count('id'))
    type_stats = leaves.values('leave_type').annotate(count=Count('id'), days=Sum('total_days'))

    context = {
        'leaves': leaves[:150],
        'year': year,
        'stats': stats,
        'type_stats': type_stats,
        'total_leaves': leaves.count(),
    }
    return render(request, 'reports/leave_report.html', context)

@login_required
@hr_or_admin_required
def payroll_report(request):
    year = int(request.GET.get('year', date.today().year))
    records = PayrollRecord.objects.select_related('employee', 'employee__user', 'employee__department').filter(
        year=year
    )

    monthly_summary = records.values('month').annotate(
        total_payout=Sum('net_salary'),
        headcount=Count('id')
    ).order_by('month')

    context = {
        'year': year,
        'monthly_summary': monthly_summary,
        'records': records[:150],
        'total_year_payout': records.aggregate(total=Sum('net_salary'))['total'] or 0,
    }
    return render(request, 'reports/payroll_report.html', context)


class NumberedLandscapeCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        if self._pageNumber > 1:
            self.drawString(40, 8.5 * inch - 26, "Netcom Computers Pvt Ltd • Comprehensive HR Operations & Attendance Report")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(40, 8.5 * inch - 30, 11 * inch - 40, 8.5 * inch - 30)

        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(11 * inch - 40, 22, footer_text)
        self.drawString(40, 22, "Netcom Computers Pvt Ltd • Official Corporate Record • Confidential")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 28, 11 * inch - 40, 28)
        self.restoreState()


def _safe_image_flowable(image_field, width=1.1*inch, height=1.1*inch):
    """Safely loads an ImageField into a ReportLab Image flowable, verifying integrity."""
    if not image_field:
        return None
    try:
        path = image_field.path
        if not os.path.exists(path):
            return None
        from PIL import Image as PILImage
        with PILImage.open(path) as img:
            img.verify()
        return RLImage(path, width=width, height=height)
    except Exception:
        return None


def _build_pdf_report(target_emp, employees, attendances, leaves, daily_works, from_d, to_d, category, operator_username):
    from apps.leave_management.views import get_or_create_monthly_permission_balance

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#1e3a8a")
    secondary_color = colors.HexColor("#16a34a")
    dark_text = colors.HexColor("#0f172a")
    border_color = colors.HexColor("#cbd5e1")
    gray_bg = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'RepTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=15, leading=18, textColor=primary_color, spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        'RepSub', parent=styles['Normal'], fontName='Helvetica',
        fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"), spaceAfter=5
    )
    h1_style = ParagraphStyle(
        'RepH1', parent=styles['Heading2'], fontName='Helvetica-Bold',
        fontSize=10.5, leading=13, textColor=primary_color, spaceBefore=7, spaceAfter=4, keepWithNext=True
    )
    th_style = ParagraphStyle('RepTH', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=colors.white)
    td_style = ParagraphStyle('RepTD', fontName='Helvetica', fontSize=7, leading=9, textColor=dark_text)
    td_bold = ParagraphStyle('RepTDB', fontName='Helvetica-Bold', fontSize=7, leading=9, textColor=dark_text)

    story = []

    # Header with Logo & Title
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'netcom_logo.png')
    if not os.path.exists(logo_path):
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')

    logo_flowable = None
    if os.path.exists(logo_path):
        try:
            logo_flowable = RLImage(logo_path, width=1.1 * inch, height=0.62 * inch)
        except Exception:
            logo_flowable = Paragraph("<b>NETCOM</b>", title_style)
    else:
        logo_flowable = Paragraph("<b>NETCOM</b>", title_style)

    scope_title = f"EMPLOYEE DOSSIER & AUDIT — {target_emp.employee_code} ({target_emp.display_name()})" if target_emp else "HUMAN RESOURCES WORKFORCE REPORT"
    category_label = category.replace('_', ' ').title()
    header_text = [
        Paragraph(f"NETCOM TECHNOLOGIES — {scope_title}", title_style),
        Paragraph(
            f"<b>Date Range:</b> {from_d.strftime('%B %d, %Y')} to {to_d.strftime('%B %d, %Y')} &nbsp;|&nbsp; "
            f"<b>Category:</b> {category_label} &nbsp;|&nbsp; "
            f"<b>Generated on:</b> {date.today().strftime('%B %d, %Y')} by <b>{operator_username}</b>",
            subtitle_style
        )
    ]
    header_table = Table([[logo_flowable, header_text]], colWidths=[1.3 * inch, 9.2 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=4, spaceAfter=6))

    # Single Employee Dossier Header Card
    if target_emp:
        perm_balance = get_or_create_monthly_permission_balance(target_emp, to_d.year, to_d.month)
        emp_img = _safe_image_flowable(target_emp.profile_picture, width=1.1 * inch, height=1.1 * inch)
        if not emp_img:
            emp_img = Paragraph(
                f"<font size='18'><b>{target_emp.display_name()[:2].upper()}</b></font><br/><font size='7' color='#64748b'>No Photo</font>",
                ParagraphStyle('NoPhoto', fontName='Helvetica-Bold', alignment=1, textColor=primary_color)
            )

        doc_status_text = "Submitted & Verified ✅" if target_emp.document else "Not Uploaded ⚠️"

        info_rows = [
            [
                Paragraph("<b>Employee Code:</b>", td_bold), Paragraph(target_emp.employee_code, td_bold),
                Paragraph("<b>Full Name:</b>", td_bold), Paragraph(target_emp.display_name(), td_style),
                Paragraph("<b>Department:</b>", td_bold), Paragraph(target_emp.department.name if target_emp.department else 'General', td_style),
            ],
            [
                Paragraph("<b>Designation:</b>", td_bold), Paragraph(target_emp.designation.title if target_emp.designation else 'Staff', td_style),
                Paragraph("<b>Role:</b>", td_bold), Paragraph(target_emp.get_role_display(), td_style),
                Paragraph("<b>Joining Date:</b>", td_bold), Paragraph(str(target_emp.joining_date), td_bold),
            ],
            [
                Paragraph("<b>Email:</b>", td_bold), Paragraph(target_emp.email or '-', td_style),
                Paragraph("<b>Phone:</b>", td_bold), Paragraph(target_emp.phone or '-', td_style),
                Paragraph("<b>Basic Salary:</b>", td_bold), Paragraph(f"₹{target_emp.basic_salary}", td_style),
            ],
            [
                Paragraph("<b>Casual Leave Balance:</b>", td_bold), Paragraph(f"<b>{target_emp.casual_leave_balance} Days</b>", td_bold),
                Paragraph("<b>Remaining Permission:</b>", td_bold), Paragraph(f"<b>{perm_balance.remaining_formatted()}</b>", td_bold),
                Paragraph("<b>Submitted Document:</b>", td_bold), Paragraph(doc_status_text, td_bold),
            ],
        ]
        info_t = Table(info_rows, colWidths=[1.4 * inch, 1.8 * inch, 1.4 * inch, 1.8 * inch, 1.4 * inch, 1.6 * inch])
        info_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))

        dossier_box = Table([[emp_img, info_t]], colWidths=[1.3 * inch, 9.2 * inch])
        dossier_box.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(dossier_box)
        story.append(Spacer(1, 6))

    # KPI Summary Row
    total_punches = attendances.count()
    total_presents = attendances.filter(status='Present').count()
    total_half_days = attendances.filter(status='Half Day').count()
    total_permissions = attendances.filter(is_permission=True).count()
    total_approved_leaves = leaves.filter(status='Approved').count()
    total_work_logs = daily_works.count()

    kpi_row = [
        [
            Paragraph("<b>Total Staff:</b>", td_bold), Paragraph(str(employees.count()), td_style),
            Paragraph("<b>Punches Logged:</b>", td_bold), Paragraph(str(total_punches), td_style),
            Paragraph("<b>Full Days (>=9h):</b>", td_bold), Paragraph(str(total_presents), td_style),
            Paragraph("<b>Half Days (>=4.5h):</b>", td_bold), Paragraph(str(total_half_days), td_style),
        ],
        [
            Paragraph("<b>Permissions:</b>", td_bold), Paragraph(str(total_permissions), td_style),
            Paragraph("<b>Approved Leaves:</b>", td_bold), Paragraph(str(total_approved_leaves), td_style),
            Paragraph("<b>Daily Tasks Logged:</b>", td_bold), Paragraph(str(total_work_logs), td_style),
            Paragraph("<b>Report Status:</b>", td_bold), Paragraph("Verified Complete ✅", td_style),
        ]
    ]
    kpi_table = Table(kpi_row, colWidths=[1.4 * inch, 1.2 * inch, 1.4 * inch, 1.2 * inch, 1.4 * inch, 1.2 * inch, 1.4 * inch, 1.3 * inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), gray_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 4))

    # Section 1: Employee Directory / Profiles
    if (category in ('complete', 'all', 'profiles')) and not target_emp:
        story.append(Paragraph(f"1. Employee Directory & Profiles ({employees.count()} staff)", h1_style))
        emp_table_data = [[
            Paragraph("Code", th_style),
            Paragraph("Employee Name", th_style),
            Paragraph("Department", th_style),
            Paragraph("Role", th_style),
            Paragraph("Joining Date", th_style),
            Paragraph("Basic Salary", th_style),
            Paragraph("Casual Leave Balance", th_style),
            Paragraph("Document Status", th_style),
            Paragraph("Status", th_style),
        ]]
        for emp in employees[:80]:
            doc_st = "Submitted ✅" if emp.document else "Pending ⚠️"
            emp_table_data.append([
                Paragraph(emp.employee_code, td_bold),
                Paragraph(emp.display_name(), td_style),
                Paragraph(emp.department.name if emp.department else 'General', td_style),
                Paragraph(emp.get_role_display(), td_style),
                Paragraph(str(emp.joining_date), td_style),
                Paragraph(f"₹{emp.basic_salary}", td_style),
                Paragraph(f"<b>{emp.casual_leave_balance}d</b>", td_style),
                Paragraph(doc_st, td_style),
                Paragraph("Active" if emp.is_active_employee else "Inactive", td_style),
            ])
        emp_t = Table(emp_table_data, colWidths=[1.0 * inch, 1.8 * inch, 1.4 * inch, 1.0 * inch, 1.1 * inch, 1.0 * inch, 1.1 * inch, 1.2 * inch, 0.9 * inch])
        emp_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(emp_t)
        story.append(Spacer(1, 6))

    # Section 2: Attendance Records
    if category in ('complete', 'all', 'attendance'):
        sec_num = "1" if target_emp else "2"
        story.append(Paragraph(f"{sec_num}. Attendance History & Punch Logs ({attendances.count()} records)", h1_style))
        att_table_data = [[
            Paragraph("Date", th_style),
            Paragraph("Staff Code", th_style),
            Paragraph("Employee Name", th_style),
            Paragraph("Punch In", th_style),
            Paragraph("Punch Out", th_style),
            Paragraph("Total Duration", th_style),
            Paragraph("Status", th_style),
            Paragraph("2h Permission", th_style),
            Paragraph("GPS Location / Source", th_style),
        ]]
        for att in attendances[:120]:
            status_text = att.status
            perm_str = "Yes" if att.is_permission else "No"
            loc_str = att.in_location[:35] if att.in_location else (att.update_source or 'System')
            att_table_data.append([
                Paragraph(str(att.date), td_style),
                Paragraph(att.employee.employee_code, td_bold),
                Paragraph(att.employee.display_name(), td_style),
                Paragraph(str(att.in_time)[:5] if att.in_time else '--:--', td_style),
                Paragraph(str(att.out_time)[:5] if att.out_time else '--:--', td_style),
                Paragraph(att.total_work_time, td_style),
                Paragraph(status_text, td_bold),
                Paragraph(perm_str, td_style),
                Paragraph(loc_str, td_style),
            ])
        if attendances.count() == 0:
            att_table_data.append([Paragraph("No attendance records logged in selected date range.", td_style)] + [Paragraph("", td_style)] * 8)

        att_t = Table(att_table_data, colWidths=[1.0 * inch, 1.1 * inch, 1.8 * inch, 1.0 * inch, 1.0 * inch, 1.2 * inch, 1.4 * inch, 1.0 * inch, 2.0 * inch])
        att_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(att_t)
        story.append(Spacer(1, 6))

    # Section 3: Leave Requests & Approvals
    if category in ('complete', 'all', 'leaves'):
        sec_num = "2" if target_emp else "3"
        story.append(Paragraph(f"{sec_num}. Leave Requests & Balances ({leaves.count()} records)", h1_style))
        lv_table_data = [[
            Paragraph("Staff", th_style),
            Paragraph("Type", th_style),
            Paragraph("From - To", th_style),
            Paragraph("Days", th_style),
            Paragraph("Status", th_style),
            Paragraph("Classification", th_style),
            Paragraph("Reason / Purpose", th_style),
            Paragraph("Reviewer / Audit", th_style),
        ]]
        for lv in leaves[:80]:
            lv_table_data.append([
                Paragraph(f"<b>{lv.employee.employee_code}</b> {lv.employee.display_name()}", td_style),
                Paragraph(lv.leave_type, td_bold),
                Paragraph(f"{lv.from_date.strftime('%b %d')} - {lv.to_date.strftime('%b %d')}", td_style),
                Paragraph(f"{lv.total_days}d", td_bold),
                Paragraph(lv.status, td_bold),
                Paragraph(lv.approval_type or ('Paid' if lv.is_paid else 'Unpaid'), td_style),
                Paragraph((lv.reason[:45] + '...') if len(lv.reason) > 45 else lv.reason, td_style),
                Paragraph(lv.reviewed_by.username if lv.reviewed_by else '-', td_style),
            ])
        if leaves.count() == 0:
            lv_table_data.append([Paragraph("No leave applications found in selected date range.", td_style)] + [Paragraph("", td_style)] * 7)

        lv_t = Table(lv_table_data, colWidths=[2.0 * inch, 1.3 * inch, 1.4 * inch, 0.7 * inch, 1.0 * inch, 1.3 * inch, 2.0 * inch, 0.8 * inch])
        lv_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(lv_t)
        story.append(Spacer(1, 6))

    # Section 4: Daily Work Accomplishments
    if category in ('complete', 'all', 'daily_work'):
        sec_num = "3" if target_emp else "4"
        story.append(Paragraph(f"{sec_num}. Daily Work Updates & Task Accomplishments ({daily_works.count()} records)", h1_style))
        wk_table_data = [[
            Paragraph("Date", th_style),
            Paragraph("Staff", th_style),
            Paragraph("Project", th_style),
            Paragraph("Work Accomplishments", th_style),
            Paragraph("Off-Site", th_style),
            Paragraph("Status", th_style),
            Paragraph("Has Photo", th_style),
        ]]
        for wk in daily_works[:60]:
            wk_table_data.append([
                Paragraph(str(wk.date), td_style),
                Paragraph(f"<b>{wk.employee.employee_code}</b> {wk.employee.display_name()}", td_style),
                Paragraph(wk.project_name, td_bold),
                Paragraph((wk.work_details[:55] + '...') if len(wk.work_details) > 55 else wk.work_details, td_style),
                Paragraph("Yes" if wk.is_offsite else "No", td_style),
                Paragraph(wk.status, td_style),
                Paragraph("Yes 📸" if bool(wk.work_image) else "No", td_style),
            ])
        if daily_works.count() == 0:
            wk_table_data.append([Paragraph("No daily work logs recorded in selected date range.", td_style)] + [Paragraph("", td_style)] * 6)

        wk_t = Table(wk_table_data, colWidths=[1.0 * inch, 1.8 * inch, 1.6 * inch, 3.6 * inch, 0.8 * inch, 0.9 * inch, 0.8 * inch])
        wk_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(wk_t)
        story.append(Spacer(1, 6))

    # Section 5: Submitted Documents & Attachments Verification
    if category in ('complete', 'all', 'documents'):
        sec_num = "4" if target_emp else "5"
        story.append(Paragraph(f"{sec_num}. Submitted Documents & File Attachments Verification", h1_style))
        doc_table_data = [[
            Paragraph("Staff Code", th_style),
            Paragraph("Employee Name", th_style),
            Paragraph("Profile Picture", th_style),
            Paragraph("Submitted Document Name", th_style),
            Paragraph("File Availability", th_style),
            Paragraph("Audit / Verification Notes", th_style),
        ]]
        for emp in employees[:80]:
            has_pic = "Uploaded ✅" if bool(emp.profile_picture) else "None"
            doc_name = os.path.basename(emp.document.name) if emp.document else "No Document Uploaded"
            doc_avail = "Available on Disk ✅" if (emp.document and os.path.exists(emp.document.path)) else ("Missing File" if emp.document else "-")
            doc_table_data.append([
                Paragraph(emp.employee_code, td_bold),
                Paragraph(emp.display_name(), td_style),
                Paragraph(has_pic, td_style),
                Paragraph(doc_name, td_style),
                Paragraph(doc_avail, td_style),
                Paragraph("Download ZIP Bundle to extract actual files" if emp.document else "Submission pending", td_style),
            ])
        doc_t = Table(doc_table_data, colWidths=[1.1 * inch, 2.0 * inch, 1.4 * inch, 2.5 * inch, 1.6 * inch, 1.9 * inch])
        doc_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(doc_t)

    doc.build(story, canvasmaker=NumberedLandscapeCanvas)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def _build_excel_report(target_emp, employees, attendances, leaves, daily_works, from_d, to_d, category, operator_username):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws_main = wb.active

    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')
    sub_header_fill = PatternFill(start_color='16A34A', end_color='16A34A', fill_type='solid')
    title_font = Font(name='Calibri', size=15, bold=True, color='1E3A8A')
    bold_font = Font(name='Calibri', size=11, bold=True)
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # 1. Summary Sheet
    ws_main.title = "Executive Summary"
    ws_main.views.sheetView[0].showGridLines = True
    scope_str = f"Employee {target_emp.employee_code} - {target_emp.display_name()}" if target_emp else "Company-Wide Workforce"
    ws_main['A1'] = f"NETCOM COMPUTERS PVT LTD — HR REPORT: {scope_str.upper()}"
    ws_main['A1'].font = title_font
    ws_main['A2'] = f"Date Range: {from_d.strftime('%b %d, %Y')} to {to_d.strftime('%b %d, %Y')} | Category: {category.title()} | Generated: {date.today().strftime('%b %d, %Y')} by {operator_username}"
    ws_main['A2'].font = Font(name='Calibri', size=10, italic=True, color='475569')

    summary_metrics = [
        ("Report Scope", scope_str),
        ("Total Employees in Scope", employees.count()),
        ("Total Attendance Records (Date Range)", attendances.count()),
        ("Full-Day Attendance Logs (>=9h)", attendances.filter(status='Present').count()),
        ("Half-Day Attendance Logs (>=4.5h)", attendances.filter(status='Half Day').count()),
        ("Approved Permissions", attendances.filter(is_permission=True).count()),
        ("Approved Leave Records", leaves.filter(status='Approved').count()),
        ("Daily Work Logs Submitted", daily_works.count()),
    ]
    ws_main['A4'] = "Key Performance Indicator (KPI)"
    ws_main['B4'] = "Metric Value"
    ws_main['A4'].font = header_font
    ws_main['A4'].fill = sub_header_fill
    ws_main['B4'].font = header_font
    ws_main['B4'].fill = sub_header_fill

    for r_i, (kpi, val) in enumerate(summary_metrics, 5):
        ws_main.cell(row=r_i, column=1, value=kpi).border = thin_border
        c = ws_main.cell(row=r_i, column=2, value=str(val))
        c.font = bold_font
        c.border = thin_border

    ws_main.column_dimensions['A'].width = 38
    ws_main.column_dimensions['B'].width = 30

    # 2. Profiles / Directory Sheet
    if category in ('complete', 'all', 'profiles'):
        ws_emp = wb.create_sheet(title="Employee Profiles")
        ws_emp.views.sheetView[0].showGridLines = True
        emp_cols = [
            "Employee Code", "Full Name", "Username", "Email", "Phone",
            "Department", "Designation", "Role", "Joining Date", "Basic Salary",
            "Casual Leave Balance", "Document Uploaded", "Profile Picture", "Account Status"
        ]
        for col_num, h_text in enumerate(emp_cols, 1):
            cell = ws_emp.cell(row=1, column=col_num, value=h_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        for r_idx, emp in enumerate(employees, 2):
            ws_emp.cell(row=r_idx, column=1, value=emp.employee_code).border = thin_border
            ws_emp.cell(row=r_idx, column=2, value=emp.display_name()).border = thin_border
            ws_emp.cell(row=r_idx, column=3, value=emp.user.username).border = thin_border
            ws_emp.cell(row=r_idx, column=4, value=emp.email or '').border = thin_border
            ws_emp.cell(row=r_idx, column=5, value=emp.phone or '').border = thin_border
            ws_emp.cell(row=r_idx, column=6, value=emp.department.name if emp.department else 'General').border = thin_border
            ws_emp.cell(row=r_idx, column=7, value=emp.designation.title if emp.designation else 'Staff').border = thin_border
            ws_emp.cell(row=r_idx, column=8, value=emp.get_role_display()).border = thin_border
            ws_emp.cell(row=r_idx, column=9, value=str(emp.joining_date)).border = thin_border
            ws_emp.cell(row=r_idx, column=10, value=float(emp.basic_salary)).border = thin_border
            ws_emp.cell(row=r_idx, column=11, value=emp.casual_leave_balance).border = thin_border
            ws_emp.cell(row=r_idx, column=12, value="Yes (Available)" if emp.document else "No").border = thin_border
            ws_emp.cell(row=r_idx, column=13, value="Yes" if emp.profile_picture else "No").border = thin_border
            ws_emp.cell(row=r_idx, column=14, value="Active" if emp.is_active_employee else "Inactive").border = thin_border

        for col in ws_emp.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws_emp.column_dimensions[col[0].column_letter].width = max(max_len + 3, 12)

    # 3. Attendance Sheet
    if category in ('complete', 'all', 'attendance'):
        ws_att = wb.create_sheet(title="Attendance History")
        ws_att.views.sheetView[0].showGridLines = True
        att_cols = [
            "Date", "Employee Code", "Employee Name", "Department",
            "Punch In", "Punch Out", "Total Work Duration", "Status",
            "2h Permission", "Leave Type", "Punch Location / GPS", "Update Source"
        ]
        for col_num, h_text in enumerate(att_cols, 1):
            cell = ws_att.cell(row=1, column=col_num, value=h_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        for r_idx, att in enumerate(attendances, 2):
            ws_att.cell(row=r_idx, column=1, value=str(att.date)).border = thin_border
            ws_att.cell(row=r_idx, column=2, value=att.employee.employee_code).border = thin_border
            ws_att.cell(row=r_idx, column=3, value=att.employee.display_name()).border = thin_border
            ws_att.cell(row=r_idx, column=4, value=att.employee.department.name if att.employee.department else '-').border = thin_border
            ws_att.cell(row=r_idx, column=5, value=str(att.in_time)[:5] if att.in_time else '--:--').border = thin_border
            ws_att.cell(row=r_idx, column=6, value=str(att.out_time)[:5] if att.out_time else '--:--').border = thin_border
            ws_att.cell(row=r_idx, column=7, value=att.total_work_time).border = thin_border
            ws_att.cell(row=r_idx, column=8, value=att.status).border = thin_border
            ws_att.cell(row=r_idx, column=9, value="Yes" if att.is_permission else "No").border = thin_border
            ws_att.cell(row=r_idx, column=10, value=att.leave_type or '-').border = thin_border
            ws_att.cell(row=r_idx, column=11, value=att.in_location or '-').border = thin_border
            ws_att.cell(row=r_idx, column=12, value=att.update_source or 'System').border = thin_border

        for col in ws_att.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws_att.column_dimensions[col[0].column_letter].width = max(max_len + 3, 12)

    # 4. Leave Requests Sheet
    if category in ('complete', 'all', 'leaves'):
        ws_lv = wb.create_sheet(title="Leave Requests")
        ws_lv.views.sheetView[0].showGridLines = True
        lv_cols = [
            "Request ID", "Employee Code", "Employee Name", "Leave Type",
            "From Date", "To Date", "Total Days", "Status",
            "Classification", "Reason / Purpose", "Reviewer", "Rejection Reason"
        ]
        for col_num, h_text in enumerate(lv_cols, 1):
            cell = ws_lv.cell(row=1, column=col_num, value=h_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        for r_idx, lv in enumerate(leaves, 2):
            ws_lv.cell(row=r_idx, column=1, value=lv.id).border = thin_border
            ws_lv.cell(row=r_idx, column=2, value=lv.employee.employee_code).border = thin_border
            ws_lv.cell(row=r_idx, column=3, value=lv.employee.display_name()).border = thin_border
            ws_lv.cell(row=r_idx, column=4, value=lv.leave_type).border = thin_border
            ws_lv.cell(row=r_idx, column=5, value=str(lv.from_date)).border = thin_border
            ws_lv.cell(row=r_idx, column=6, value=str(lv.to_date)).border = thin_border
            ws_lv.cell(row=r_idx, column=7, value=lv.total_days).border = thin_border
            ws_lv.cell(row=r_idx, column=8, value=lv.status).border = thin_border
            ws_lv.cell(row=r_idx, column=9, value=lv.approval_type or ('Paid' if lv.is_paid else 'Unpaid')).border = thin_border
            ws_lv.cell(row=r_idx, column=10, value=lv.reason).border = thin_border
            ws_lv.cell(row=r_idx, column=11, value=lv.reviewed_by.username if lv.reviewed_by else '-').border = thin_border
            ws_lv.cell(row=r_idx, column=12, value=lv.rejection_reason or '-').border = thin_border

        for col in ws_lv.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws_lv.column_dimensions[col[0].column_letter].width = max(max_len + 3, 12)

    # 5. Daily Work Sheet
    if category in ('complete', 'all', 'daily_work'):
        ws_wk = wb.create_sheet(title="Daily Work Updates")
        ws_wk.views.sheetView[0].showGridLines = True
        wk_cols = [
            "Date", "Employee Code", "Employee Name", "Project / Module",
            "Work Accomplishments", "Status", "Off-Site Activity", "Location Notes", "Has Image"
        ]
        for col_num, h_text in enumerate(wk_cols, 1):
            cell = ws_wk.cell(row=1, column=col_num, value=h_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        for r_idx, wk in enumerate(daily_works, 2):
            ws_wk.cell(row=r_idx, column=1, value=str(wk.date)).border = thin_border
            ws_wk.cell(row=r_idx, column=2, value=wk.employee.employee_code).border = thin_border
            ws_wk.cell(row=r_idx, column=3, value=wk.employee.display_name()).border = thin_border
            ws_wk.cell(row=r_idx, column=4, value=wk.project_name).border = thin_border
            ws_wk.cell(row=r_idx, column=5, value=wk.work_details).border = thin_border
            ws_wk.cell(row=r_idx, column=6, value=wk.status).border = thin_border
            ws_wk.cell(row=r_idx, column=7, value="Yes (Off-Site)" if wk.is_offsite else "No").border = thin_border
            ws_wk.cell(row=r_idx, column=8, value=wk.location_notes or '-').border = thin_border
            ws_wk.cell(row=r_idx, column=9, value="Yes" if bool(wk.work_image) else "No").border = thin_border

        for col in ws_wk.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws_wk.column_dimensions[col[0].column_letter].width = max(max_len + 3, 12)

    # 6. Documents Sheet
    if category in ('complete', 'all', 'documents'):
        ws_doc = wb.create_sheet(title="Documents & Files")
        ws_doc.views.sheetView[0].showGridLines = True
        doc_cols = [
            "Employee Code", "Employee Name", "Profile Picture Uploaded",
            "Submitted Document Name", "File Status", "Verification Notes"
        ]
        for col_num, h_text in enumerate(doc_cols, 1):
            cell = ws_doc.cell(row=1, column=col_num, value=h_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        for r_idx, emp in enumerate(employees, 2):
            doc_name = os.path.basename(emp.document.name) if emp.document else "None"
            doc_status = "Available on Disk" if (emp.document and os.path.exists(emp.document.path)) else ("Missing" if emp.document else "Not Uploaded")
            ws_doc.cell(row=r_idx, column=1, value=emp.employee_code).border = thin_border
            ws_doc.cell(row=r_idx, column=2, value=emp.display_name()).border = thin_border
            ws_doc.cell(row=r_idx, column=3, value="Yes" if emp.profile_picture else "No").border = thin_border
            ws_doc.cell(row=r_idx, column=4, value=doc_name).border = thin_border
            ws_doc.cell(row=r_idx, column=5, value=doc_status).border = thin_border
            ws_doc.cell(row=r_idx, column=6, value="Actual files included in ZIP bundle download").border = thin_border

        for col in ws_doc.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws_doc.column_dimensions[col[0].column_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _build_zip_bundle(target_emp, employees, attendances, leaves, daily_works, from_d, to_d, category, operator_username):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Generate & embed PDF report inside ZIP
        pdf_bytes = _build_pdf_report(target_emp, employees, attendances, leaves, daily_works, from_d, to_d, category, operator_username)
        report_pdf_name = f"NETCOM_Report_{target_emp.employee_code if target_emp else 'Workforce'}_{from_d.strftime('%Y%m%d')}_to_{to_d.strftime('%Y%m%d')}.pdf"
        zf.writestr(report_pdf_name, pdf_bytes)

        # 2. Generate & embed Excel report inside ZIP
        excel_bytes = _build_excel_report(target_emp, employees, attendances, leaves, daily_works, from_d, to_d, category, operator_username)
        report_excel_name = f"NETCOM_Report_{target_emp.employee_code if target_emp else 'Workforce'}_{from_d.strftime('%Y%m%d')}_to_{to_d.strftime('%Y%m%d')}.xlsx"
        zf.writestr(report_excel_name, excel_bytes)

        # 3. Add Manifest / Readme
        manifest = [
            "================================================================================",
            "NETCOM EMPLOYEE MANAGEMENT SYSTEM PRO — HR DATA EXPORT BUNDLE",
            "================================================================================",
            f"Generated On  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Generated By  : {operator_username}",
            f"Scope         : {'Employee: ' + target_emp.employee_code + ' - ' + target_emp.display_name() if target_emp else 'Company-Wide Workforce'}",
            f"Date Range    : {from_d.strftime('%Y-%m-%d')} to {to_d.strftime('%Y-%m-%d')}",
            f"Category      : {category.title()}",
            "--------------------------------------------------------------------------------",
            "CONTENTS INCLUDED IN THIS ARCHIVE:",
            f"1. {report_pdf_name} (Complete formatted PDF document)",
            f"2. {report_excel_name} (Structured Excel workbook)",
            "3. Actual uploaded employee files (ID proofs, resumes, credentials, photos)",
            "================================================================================",
        ]

        doc_count = 0
        photo_count = 0
        work_photo_count = 0

        # 4. Attach actual files
        for emp in employees:
            folder_prefix = "" if target_emp else f"Employees/{emp.employee_code}_{emp.display_name().replace(' ', '_')}/"

            # Profile Picture
            if emp.profile_picture:
                try:
                    if os.path.exists(emp.profile_picture.path):
                        ext = os.path.splitext(emp.profile_picture.name)[1] or '.jpg'
                        with open(emp.profile_picture.path, 'rb') as f:
                            zf.writestr(f"{folder_prefix}Profile_Photos/{emp.employee_code}_Photo{ext}", f.read())
                        photo_count += 1
                except Exception:
                    pass

            # Submitted Document
            if emp.document:
                try:
                    if os.path.exists(emp.document.path):
                        orig_basename = os.path.basename(emp.document.name)
                        with open(emp.document.path, 'rb') as f:
                            zf.writestr(f"{folder_prefix}Submitted_Documents/{emp.employee_code}_{orig_basename}", f.read())
                        doc_count += 1
                except Exception:
                    pass

        # 5. Off-Site Daily Work Photos
        if category in ('complete', 'all', 'daily_work'):
            for wk in daily_works:
                if wk.work_image:
                    try:
                        if os.path.exists(wk.work_image.path):
                            folder_prefix = "" if target_emp else f"Employees/{wk.employee.employee_code}_{wk.employee.display_name().replace(' ', '_')}/"
                            img_base = os.path.basename(wk.work_image.name)
                            zf.writestr(f"{folder_prefix}Work_Photos/{wk.date}_{img_base}", wk.work_image.read())
                            work_photo_count += 1
                    except Exception:
                        pass

        manifest.append(f"• Total Submitted Documents Attached: {doc_count}")
        manifest.append(f"• Total Profile Pictures Attached    : {photo_count}")
        manifest.append(f"• Total Work Verification Photos     : {work_photo_count}")
        manifest.append("================================================================================")
        zf.writestr("README_Manifest.txt", "\n".join(manifest))

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@login_required
@hr_or_admin_required
def complete_hr_report_export(request):
    """
    Comprehensive Employee Reports & Data Export Controller:
    - Filters by individual employee or company-wide workforce
    - Custom date-to-date range filtering
    - Specific category filtering (complete, attendance, leaves, daily_work, profiles, documents)
    - Multi-format downloading (PDF, Excel, ZIP Bundle with actual files attached)
    """
    today = date.today()
    emp_param = (request.GET.get('employee_id') or request.GET.get('employee') or 'all').strip()
    category = (request.GET.get('category') or 'complete').strip().lower()
    start_date_str = request.GET.get('from_date') or request.GET.get('start_date') or (today - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date_str = request.GET.get('to_date') or request.GET.get('end_date') or today.strftime('%Y-%m-%d')
    export_format = (request.GET.get('format') or 'pdf').strip().lower()

    try:
        from_d = datetime.strptime(start_date_str[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        from_d = today - timedelta(days=30)

    try:
        to_d = datetime.strptime(end_date_str[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        to_d = today

    if to_d < from_d:
        from_d, to_d = to_d, from_d

    # Identify target employee if specified
    target_emp = None
    if emp_param and emp_param != 'all':
        try:
            target_emp = Employee.objects.select_related('user', 'department', 'designation').filter(
                Q(id=int(emp_param)) | Q(employee_code=emp_param)
            ).first()
        except (ValueError, TypeError):
            target_emp = Employee.objects.select_related('user', 'department', 'designation').filter(
                employee_code=emp_param
            ).first()

    from apps.attendance.models import DailyWork

    # Data querying
    if target_emp:
        employees = Employee.objects.select_related('user', 'department', 'designation').filter(id=target_emp.id)
        attendances = Attendance.objects.select_related('employee', 'employee__user', 'employee__department').filter(
            employee=target_emp, date__range=[from_d, to_d]
        ).order_by('-date')
        leaves = LeaveRequest.objects.select_related('employee', 'employee__user', 'reviewed_by').filter(
            employee=target_emp, from_date__lte=to_d, to_date__gte=from_d
        ).order_by('-from_date')
        daily_works = DailyWork.objects.select_related('employee', 'employee__user').filter(
            employee=target_emp, date__range=[from_d, to_d]
        ).order_by('-date')
    else:
        employees = Employee.objects.select_related('user', 'department', 'designation').all().order_by('employee_code')
        attendances = Attendance.objects.select_related('employee', 'employee__user', 'employee__department').filter(
            date__range=[from_d, to_d]
        ).order_by('-date', 'employee__employee_code')
        leaves = LeaveRequest.objects.select_related('employee', 'employee__user', 'reviewed_by').filter(
            from_date__lte=to_d, to_date__gte=from_d
        ).order_by('-from_date')
        daily_works = DailyWork.objects.select_related('employee', 'employee__user').filter(
            date__range=[from_d, to_d]
        ).order_by('-date')

    # Base filename components
    scope_tag = target_emp.employee_code if target_emp else "Workforce"
    cat_tag = category.title()
    date_tag = f"{from_d.strftime('%Y%m%d')}_to_{to_d.strftime('%Y%m%d')}"

    # 1. ZIP EXPORT (.zip)
    if export_format == 'zip':
        zip_bytes = _build_zip_bundle(
            target_emp, employees, attendances, leaves, daily_works,
            from_d, to_d, category, request.user.username
        )
        filename = f"NETCOM_{scope_tag}_{cat_tag}_{date_tag}.zip"
        response = HttpResponse(zip_bytes, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # 2. EXCEL EXPORT (.xlsx)
    elif export_format in ('excel', 'xlsx'):
        excel_bytes = _build_excel_report(
            target_emp, employees, attendances, leaves, daily_works,
            from_d, to_d, category, request.user.username
        )
        filename = f"NETCOM_{scope_tag}_{cat_tag}_{date_tag}.xlsx"
        response = HttpResponse(
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # 3. PDF EXPORT (.pdf - default)
    else:
        pdf_bytes = _build_pdf_report(
            target_emp, employees, attendances, leaves, daily_works,
            from_d, to_d, category, request.user.username
        )
        filename = f"NETCOM_{scope_tag}_{cat_tag}_{date_tag}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

