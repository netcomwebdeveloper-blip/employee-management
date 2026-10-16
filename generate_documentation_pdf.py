import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
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

        # Running Header (Skip on Cover Page)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Netcom Computers Pvt Ltd — Employee Management System Pro | Comprehensive Documentation")
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "System Reference Manual")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer (All Pages)
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 30, footer_text)
        self.drawString(54, 30, "Confidential & Proprietary • Netcom Computers Pvt Ltd • All Rights Reserved")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 42, 8.5 * inch - 54, 42)
        self.restoreState()


def build_documentation_pdf(filename="Netcom_Employee_Management_System_Documentation.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    c_primary = colors.HexColor("#1e3a8a")     # Deep corporate blue
    c_secondary = colors.HexColor("#0284c7")   # Light accent blue
    c_dark = colors.HexColor("#0f172a")        # Dark slate body
    c_muted = colors.HexColor("#475569")       # Muted text
    c_border = colors.HexColor("#cbd5e1")      # Border slate
    c_light_bg = colors.HexColor("#f8fafc")    # Light panel bg
    c_success = colors.HexColor("#059669")     # Green
    c_warning = colors.HexColor("#d97706")     # Amber
    c_danger = colors.HexColor("#dc2626")      # Red

    # Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=c_primary,
        alignment=0,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_muted,
        alignment=0,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_secondary,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_dark,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_dark,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#1e40af")
    )

    table_header_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=0
    )

    table_cell_style = ParagraphStyle(
        'TD',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_dark
    )

    table_cell_bold = ParagraphStyle(
        'TDBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=c_dark
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # =========================================================================
    # 1. COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("NETCOM COMPUTERS PVT LTD", ParagraphStyle('CompanyPreHeader', fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=c_secondary, textTransform='uppercase', spaceAfter=6)))
    story.append(Paragraph("Employee Management System Pro", title_style))
    story.append(Paragraph("Complete Technical Architecture, Operational Workflows & System Reference Manual", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=c_primary, spaceBefore=4, spaceAfter=20))

    cover_meta_data = [
        [Paragraph("<b>Document Version:</b>", table_cell_bold), Paragraph("Version 2.4 (Enterprise Edition)", table_cell_style)],
        [Paragraph("<b>Publication Date:</b>", table_cell_bold), Paragraph("October 2026", table_cell_style)],
        [Paragraph("<b>Primary Framework:</b>", table_cell_bold), Paragraph("Django 5.0.6 (Python 3.12+)", table_cell_style)],
        [Paragraph("<b>Database Engine:</b>", table_cell_bold), Paragraph("MySQL 8.0 / SQLite Multi-Environment Compatibility", table_cell_style)],
        [Paragraph("<b>Frontend Technologies:</b>", table_cell_bold), Paragraph("Modern HTML5, Vanilla JavaScript (ES6+), CSS3 Flexbox/Grid", table_cell_style)],
        [Paragraph("<b>Document Scope:</b>", table_cell_bold), Paragraph("Architecture, Dashboards, Biometric/Selfie Attendance, Payroll, Leave, & Deployment", table_cell_style)],
        [Paragraph("<b>Author / Organization:</b>", table_cell_bold), Paragraph("Netcom Computers Engineering & Software Architecture Team", table_cell_style)],
    ]
    meta_table = Table(cover_meta_data, colWidths=[1.8 * inch, 5.2 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_light_bg),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 24))

    exec_summary_box = [
        [Paragraph("<b>EXECUTIVE OVERVIEW & SYSTEM PURPOSE</b>", ParagraphStyle('BoxTitle', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=c_primary))],
        [Paragraph(
            "The <b>Netcom Employee Management System Pro</b> is a mission-critical enterprise human resource "
            "and workforce management platform built to centralize personnel management, real-time verified attendance, "
            "department organization, leave requests, daily task scheduling, and attendance-based salary calculations. "
            "Equipped with modern HTML5 Geolocation access and live camera selfie capture for mandatory daily punch-in/out, "
            "role-based dashboard segregation (Employee, HR Manager, Administrator), monthly casual leave auto-credits, "
            "sub-day permission management, and audit-trailed manual corrections, the system provides automated, "
            "verifiable, and compliant workforce operations.",
            body_style
        )]
    ]
    sum_table = Table(exec_summary_box, colWidths=[7.0 * inch])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#bfdbfe")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(sum_table)

    story.append(PageBreak())

    # =========================================================================
    # 2. TABLE OF CONTENTS
    # =========================================================================
    story.append(Paragraph("Table of Contents", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_border, spaceBefore=2, spaceAfter=10))

    toc_data = [
        [Paragraph("<b>Section 1:</b> Project Overview & Business Objectives", table_cell_bold), Paragraph("Page 3", table_cell_style)],
        [Paragraph("<b>Section 2:</b> Technology Stack & Architecture", table_cell_bold), Paragraph("Page 3", table_cell_style)],
        [Paragraph("<b>Section 3:</b> Database Relational Schema & Models", table_cell_bold), Paragraph("Page 4", table_cell_style)],
        [Paragraph("<b>Section 4:</b> Login, Authentication & Role Access Control", table_cell_bold), Paragraph("Page 6", table_cell_style)],
        [Paragraph("<b>Section 5:</b> Employee Dashboard (Self-Service Portal)", table_cell_bold), Paragraph("Page 7", table_cell_style)],
        [Paragraph("<b>Section 6:</b> HR Operations Dashboard", table_cell_bold), Paragraph("Page 8", table_cell_style)],
        [Paragraph("<b>Section 7:</b> Admin Dashboard & System Governance", table_cell_bold), Paragraph("Page 9", table_cell_style)],
        [Paragraph("<b>Section 8:</b> Attendance Tracking, GPS & Live Selfie Verification", table_cell_bold), Paragraph("Page 10", table_cell_style)],
        [Paragraph("<b>Section 9:</b> Working Hours, Daily Midnight Reset & Rules", table_cell_bold), Paragraph("Page 11", table_cell_style)],
        [Paragraph("<b>Section 10:</b> Leave Management, Monthly Credit & Restoration", table_cell_bold), Paragraph("Page 12", table_cell_style)],
        [Paragraph("<b>Section 11:</b> Two-Hour Permission Request & Review Workflow", table_cell_bold), Paragraph("Page 13", table_cell_style)],
        [Paragraph("<b>Section 12:</b> Office Holidays & Calendar Synchronization", table_cell_bold), Paragraph("Page 14", table_cell_style)],
        [Paragraph("<b>Section 13:</b> Daily Work Updates & Task Planning", table_cell_bold), Paragraph("Page 14", table_cell_style)],
        [Paragraph("<b>Section 14:</b> Salary & Payroll Calculation Engine", table_cell_bold), Paragraph("Page 15", table_cell_style)],
        [Paragraph("<b>Section 15:</b> Reporting, Analytics, Excel & PDF Exports", table_cell_bold), Paragraph("Page 16", table_cell_style)],
        [Paragraph("<b>Section 16:</b> Security, Error Handling & System Resilience", table_cell_bold), Paragraph("Page 17", table_cell_style)],
        [Paragraph("<b>Section 17:</b> Database Backup, Restoration & Deployment Guide", table_cell_bold), Paragraph("Page 18", table_cell_style)],
    ]
    t_toc = Table(toc_data, colWidths=[5.8 * inch, 1.2 * inch])
    t_toc.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 1: PROJECT OVERVIEW & OBJECTIVES
    # =========================================================================
    story.append(Paragraph("1. Project Overview & Business Objectives", h1_style))
    story.append(Paragraph(
        "Netcom Computers Pvt Ltd operates a high-performance workforce across diverse technical, administrative, "
        "and client-facing projects. Managing this workforce requires transparency, prompt attendance accountability, "
        "and accurate payroll compensation. The <b>Netcom Employee Management System Pro</b> was engineered to replace manual, "
        "error-prone attendance sheets and scattered messaging channels with a single, hardened web application.",
        body_style
    ))
    story.append(Paragraph("Key Core Objectives:", h2_style))
    story.append(Paragraph("• <b>Dual-Verification Attendance:</b> Eliminate buddy-punching and false reporting through mandatory GPS geolocation and real-time camera snapshot verification.", bullet_style))
    story.append(Paragraph("• <b>Automated Attendance Evaluation:</b> Evaluate working hours based on standard full-day (9+ hours) and half-day (4.5 to 9 hours) thresholds calculated on the local calendar day.", bullet_style))
    story.append(Paragraph("• <b>Accurate Payroll Synchronization:</b> Automatically calculate daily rates and salary deductions based on unexcused absences, half-days, or uncorrected missing punches.", bullet_style))
    story.append(Paragraph("• <b>Leave & 2-Hour Permission Workflows:</b> Allow employees to request leave or short permissions with live duration validation, with automated HR review and zero salary deduction upon approval.", bullet_style))
    story.append(Paragraph("• <b>Unified Administrative Governance:</b> Provide real-time KPI metrics, audit logs for manual overrides, broadcast announcements, and one-click PDF/Excel report downloads.", bullet_style))
    story.append(Spacer(1, 8))

    # =========================================================================
    # SECTION 2: TECHNOLOGY STACK & ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("2. Technology Stack & Architectural Pattern", h1_style))
    story.append(Paragraph(
        "The project follows Django's clean <b>Model-View-Template (MVT)</b> pattern, separating business logic, "
        "data models, and user presentation into maintainable, modular apps under the <code>apps/</code> directory.",
        body_style
    ))

    tech_table_data = [
        [Paragraph("<b>Component / Layer</b>", table_header_style), Paragraph("<b>Technology Selected</b>", table_header_style), Paragraph("<b>Architectural Role & Description</b>", table_header_style)],
        [Paragraph("<b>Backend Web Framework</b>", table_cell_bold), Paragraph("Django 5.0.6 (Python 3.12+)", table_cell_style), Paragraph("Handles URL routing, ORM database transactions, session security, authentication, and view logic.", table_cell_style)],
        [Paragraph("<b>Database Layer</b>", table_cell_bold), Paragraph("MySQL 8.0 / SQLite", table_cell_style), Paragraph("Provides ACID compliance, relational integrity, foreign key constraints, and persistent indexing.", table_cell_style)],
        [Paragraph("<b>Frontend Template Engine</b>", table_cell_bold), Paragraph("Django Templates + HTML5", table_cell_style), Paragraph("Server-side HTML rendering with global context processors (branding, banner, popup, current user role).", table_cell_style)],
        [Paragraph("<b>Client-Side Scripting</b>", table_cell_bold), Paragraph("Vanilla JavaScript (ES6+)", table_cell_style), Paragraph("MediaDevices Camera API snapshot capture, Geolocation API GPS positioning, and dynamic forms.", table_cell_style)],
        [Paragraph("<b>User Interface Styling</b>", table_cell_bold), Paragraph("Custom CSS3 Design System", table_cell_style), Paragraph("Modern typography, responsive CSS Grid and Flexbox layouts, status badges, and modal overlays.", table_cell_style)],
        [Paragraph("<b>Document Generation</b>", table_cell_bold), Paragraph("ReportLab & OpenPyXL", table_cell_style), Paragraph("High-speed programmatic PDF generation (audit reports, guidebooks) and Excel spreadsheet export.", table_cell_style)],
        [Paragraph("<b>Production Web Server</b>", table_cell_bold), Paragraph("Gunicorn + WhiteNoise", table_cell_style), Paragraph("WSGI HTTP server handling production concurrency with efficient static asset caching and compression.", table_cell_style)],
    ]
    t_tech = Table(tech_table_data, colWidths=[1.8 * inch, 1.8 * inch, 3.4 * inch])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_tech)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Modular Application Architecture:", h2_style))
    story.append(Paragraph("• <code>apps.users</code>: Custom authentication, login, logout, profile update, role decorators, and global context processors.", bullet_style))
    story.append(Paragraph("• <code>apps.employees</code>: Employee master record, staff registry, document storage, profile pictures, and password view/edit.", bullet_style))
    story.append(Paragraph("• <code>apps.departments</code>: Organizational departments and designations.", bullet_style))
    story.append(Paragraph("• <code>apps.attendance</code>: Self-service punch, GPS/selfie validation, audit logging, manual overrides, and work logs.", bullet_style))
    story.append(Paragraph("• <code>apps.leave_management</code>: Leave requests, 2-hour permissions, monthly credit (1/mo), office holidays, and notifications.", bullet_style))
    story.append(Paragraph("• <code>apps.payroll</code>: Salary structures, payroll calculation engine, attendance-based deduction rules, and monthly payroll records.", bullet_style))
    story.append(Paragraph("• <code>apps.reports</code>: Workforce analytics, attendance filtering, and Excel (.xlsx) / PDF exports.", bullet_style))
    story.append(Paragraph("• <code>apps.dashboard</code>: Role-based dashboard routing (Employee, HR, Admin), calendar generation, banners, and announcements.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 3: DATABASE RELATIONAL SCHEMA & MODELS
    # =========================================================================
    story.append(Paragraph("3. Database Structure & Relational Schema", h1_style))
    story.append(Paragraph(
        "The relational schema is designed with foreign keys, data normalization, and strict data types. "
        "The central entity is <code>Employee</code>, which extends Django's native <code>auth_user</code> table via a One-to-One relationship.",
        body_style
    ))

    schema_data = [
        [Paragraph("<b>Model Name</b>", table_header_style), Paragraph("<b>Key Fields & Types</b>", table_header_style), Paragraph("<b>Relationships & Business Purpose</b>", table_header_style)],
        [
            Paragraph("<b>User</b><br/><code>django.contrib.auth</code>", table_cell_bold),
            Paragraph("username, password (hash), first_name, last_name, email, is_staff, is_superuser, is_active", table_cell_style),
            Paragraph("Standard Django user authentication model. Provides secure password hashing (PBKDF2) and session tokens.", table_cell_style)
        ],
        [
            Paragraph("<b>Employee</b><br/><code>apps.employees</code>", table_cell_bold),
            Paragraph("employee_code (Unique, Char20), role (ADMIN/HR/EMPLOYEE), joining_date (Date, Mandatory), phone, address, basic_salary, casual_leave_balance, raw_password, profile_picture, document, is_active_employee", table_cell_style),
            Paragraph("OneToOneField to User. ForeignKey to Department & Designation. Core workforce profile with operational password visibility and official joining date for HR.", table_cell_style)
        ],
        [
            Paragraph("<b>Department / Designation</b><br/><code>apps.departments</code>", table_cell_bold),
            Paragraph("name, code, description / title, department (FK)", table_cell_style),
            Paragraph("Defines company departments (IT, Sales, HR, Admin) and job titles (Software Engineer, HR Manager).", table_cell_style)
        ],
        [
            Paragraph("<b>Attendance</b><br/><code>apps.attendance</code>", table_cell_bold),
            Paragraph("date (Date), in_time, out_time (Time), status, in_photo, out_photo, in_latitude, in_longitude, in_location, total_work_minutes, is_permission, permission_hours, update_source", table_cell_style),
            Paragraph("ForeignKey to Employee. Unique constraint on (employee, date). Stores daily punch times, photos, GPS data, and computed work minutes.", table_cell_style)
        ],
        [
            Paragraph("<b>AttendanceAuditLog</b><br/><code>apps.attendance</code>", table_cell_bold),
            Paragraph("action (MANUAL_UPDATE, PUNCH_OUT_CORRECTION), old_values, new_values, changed_by (FK User), timestamp, ip_address", table_cell_style),
            Paragraph("ForeignKey to Attendance. Immutable chronological audit trail recording every administrative or HR attendance correction.", table_cell_style)
        ],
        [
            Paragraph("<b>DailyWork</b><br/><code>apps.attendance</code>", table_cell_bold),
            Paragraph("date, project_name, tasks_completed, hours_spent, is_offsite, site_location, work_image", table_cell_style),
            Paragraph("ForeignKey to Employee. Captures daily activity logs and offsite photographic proofs submitted by staff.", table_cell_style)
        ],
        [
            Paragraph("<b>DailyWorkPlan</b><br/><code>apps.attendance</code>", table_cell_bold),
            Paragraph("work_date, title, tasks, status (Assigned/In Progress/Completed/Deferred), assigned_by (FK User)", table_cell_style),
            Paragraph("ForeignKey to Employee. Allows HR to dispatch structured daily work tasks directly to the employee's portal.", table_cell_style)
        ],
        [
            Paragraph("<b>LeaveRequest</b><br/><code>apps.leave_management</code>", table_cell_bold),
            Paragraph("leave_type (Casual/Sick/Permission), from_date, to_date, total_days, reason, status (Pending/Approved/Rejected), is_paid, approval_type, reviewed_by (FK User)", table_cell_style),
            Paragraph("ForeignKey to Employee. Manages employee leave applications and 2-hour permission requests with review tracking.", table_cell_style)
        ],
        [
            Paragraph("<b>MonthlyLeaveCredit</b><br/><code>apps.leave_management</code>", table_cell_bold),
            Paragraph("year, month, casual_added (default 1), created_at", table_cell_style),
            Paragraph("Unique on (employee, year, month). Enforces the strict rule of 1 casual leave per month with zero rollover.", table_cell_style)
        ],
        [
            Paragraph("<b>MonthlyPermissionBalance</b><br/><code>apps.leave_management</code>", table_cell_bold),
            Paragraph("employee (FK), year, month, total_hours_allowed (5.00), used_hours, total_requests_allowed, used_requests_count", table_cell_style),
            Paragraph("Unique on (employee, year, month). Enforces monthly permission balance (5 hours) calculated strictly against remaining balance with zero rollover.", table_cell_style)
        ],
        [
            Paragraph("<b>OfficePaidLeave</b><br/><code>apps.leave_management</code>", table_cell_bold),
            Paragraph("date (Unique), title, description, marked_by (FK User)", table_cell_style),
            Paragraph("Official office holiday calendar. Automatically syncs all active employees with paid attendance credit.", table_cell_style)
        ],
        [
            Paragraph("<b>SalaryStructure / PayrollRecord</b><br/><code>apps.payroll</code>", table_cell_bold),
            Paragraph("basic_salary, hra, allowances, statutory_deductions / year, month, gross_salary, net_salary, deductions, remarks", table_cell_style),
            Paragraph("ForeignKey to Employee. Calculates monthly payroll, computing daily rates and attendance deductions.", table_cell_style)
        ],
        [
            Paragraph("<b>DashboardBanner / Popup</b><br/><code>apps.dashboard</code>", table_cell_bold),
            Paragraph("title, image, description, is_active, uploaded_by (FK User)", table_cell_style),
            Paragraph("Manages active hero banners and announcement popup modals across login and dashboard screens.", table_cell_style)
        ],
    ]
    t_schema = Table(schema_data, colWidths=[1.6 * inch, 2.5 * inch, 2.9 * inch])
    t_schema.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_schema)

    story.append(PageBreak())

    # =========================================================================
    # SECTION 4: LOGIN, AUTHENTICATION & ACCESS CONTROL
    # =========================================================================
    story.append(Paragraph("4. Login, Authentication & Role Access Control", h1_style))
    story.append(Paragraph(
        "Authentication is secured by Django's native session-based authentication backend. "
        "Passwords are encrypted using PBKDF2 with a SHA256 hash. The custom login view at <code>/login/</code> "
        "validates credentials and redirects users dynamically to their authorized dashboard.",
        body_style
    ))

    cred_data = [
        [Paragraph("<b>User Role</b>", table_header_style), Paragraph("<b>Username</b>", table_header_style), Paragraph("<b>Password</b>", table_header_style), Paragraph("<b>Default Landing URL & Privileges</b>", table_header_style)],
        [Paragraph("<b>Administrator</b>", table_cell_bold), Paragraph("<code>NETCOM</code>", table_cell_style), Paragraph("<code>Netcom@2026@Netcom</code>", table_cell_style), Paragraph("<code>/dashboard/</code> &bull; Full system control, Admin dashboard, HR operations, Staff registry, Django Admin.", table_cell_style)],
        [Paragraph("<b>HR Manager</b>", table_cell_bold), Paragraph("<code>hr</code>", table_cell_style), Paragraph("<code>hr12345</code>", table_cell_style), Paragraph("<code>/dashboard/</code> &bull; Complete HR Portal, attendance overrides, punch-out corrections, leave reviews, payroll.", table_cell_style)],
        [Paragraph("<b>HR Manager (Alt)</b>", table_cell_bold), Paragraph("<code>emp1</code>", table_cell_style), Paragraph("<code>emp12345</code>", table_cell_style), Paragraph("<code>/dashboard/</code> &bull; Secondary HR operational credentials with full HR administrative capabilities.", table_cell_style)],
        [Paragraph("<b>Regular Employee</b>", table_cell_bold), Paragraph("<code>emp</code>", table_cell_style), Paragraph("<code>emp12345</code>", table_cell_style), Paragraph("<code>/dashboard/</code> &bull; Employee portal, GPS/selfie punch, work submission, personal leave/permission requests.", table_cell_style)],
        [Paragraph("<b>Regular Employee</b>", table_cell_bold), Paragraph("<code>08092003</code>", table_cell_style), Paragraph("<code>emp12345</code>", table_cell_style), Paragraph("<code>/dashboard/</code> &bull; Employee portal with standard employee privileges.", table_cell_style)],
    ]
    t_cred = Table(cred_data, colWidths=[1.4 * inch, 1.2 * inch, 1.6 * inch, 2.8 * inch])
    t_cred.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_cred)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Security Safeguards & Access Decorators:", h2_style))
    story.append(Paragraph("• <b>Automatic Role Auto-Healing:</b> Built into <code>get_or_create_employee_profile()</code>. If an HR or Admin user profile is unassigned or desynchronized, the backend dynamically auto-heals their role to prevent false access denials.", bullet_style))
    story.append(Paragraph("• <code>@admin_required</code> Decorator: Restricts administrative endpoints (such as Django Admin or Admin dashboard) exclusively to superusers or accounts with <code>role='ADMIN'</code>.", bullet_style))
    story.append(Paragraph("• <code>@hr_or_admin_required</code> Decorator: Protects HR dashboard, manual overrides, missing punch-out correction, staff registration, and leave approvals from regular employee tampering.", bullet_style))
    story.append(Paragraph("• <b>Session Flush on Logout:</b> The logout endpoint calls <code>request.session.flush()</code>, eradicating stored cookies and preventing session hijacking.", bullet_style))
    story.append(Paragraph("• <b>Password Update Immediate Reflection:</b> When an employee changes their password on their profile, <code>user_profile_view()</code> saves both Django's hash and updates <code>employee.raw_password</code>, ensuring instant synchronization with the HR Dashboard registry.", bullet_style))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Employee Joining Date Governance & Policy:", h2_style))
    story.append(Paragraph("• <b>Mandatory Joining Date Capture:</b> During employee creation (both frontend form and backend processing), an official Employee Joining Date is strictly required and stored securely in <code>Employee.joining_date</code>.", bullet_style))
    story.append(Paragraph("• <b>Strict Inactive Treatment for Prior Dates:</b> The system’s attendance engine, monthly calendar views, and payroll algorithms across Employee, HR, and Admin dashboards evaluate records starting strictly from the actual joining date. All dates prior to the official joining date are rendered as inactive/non-working days (<code>pre-joining-day</code>) and are never marked as absent, flagged as missed punches, or subjected to salary deductions.", bullet_style))
    story.append(Paragraph("• <b>Live Multi-Dashboard Synchronization:</b> HR and Admin can update an employee's joining date through their respective quick-edit modals or full profile editors, immediately refreshing the employee's calendar and payroll calculations.", bullet_style))
    story.append(Paragraph("• <b>Official Document Submission & Confidentiality Governance:</b> Employees can submit or change their official document (ID proof, academic credential, certificate, or resume) at any time through their Profile Dossier or Employee Dashboard. To protect sensitive personal data, viewing and downloading documents is strictly restricted to HR Managers and Administrators; regular employees see a secure confirmation badge without view/download capabilities.", bullet_style))

    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 5: EMPLOYEE DASHBOARD (SELF-SERVICE PORTAL)
    # =========================================================================
    story.append(Paragraph("5. Employee Dashboard (Self-Service Portal)", h1_style))
    story.append(Paragraph(
        "The Employee Dashboard (<code>templates/dashboard/employee_dashboard.html</code>) is the daily hub for staff members. "
        "It provides intuitive self-service actions without granting access to company-wide management data.",
        body_style
    ))
    story.append(Paragraph("Key Employee Features & Workflows:", h2_style))
    story.append(Paragraph("1. <b>Self-Service Punch Terminal:</b> Displays the real-time clock, live video viewfinder, GPS coordinates badge, and instant Punch In / Punch Out triggers.", bullet_style))
    story.append(Paragraph("2. <b>Interactive Month Attendance Calendar:</b> Renders every day of the month with high-contrast color-coded status indicators: Solid Green (Present / Office Holiday / Sunday), Solid Yellow (Half Day), Green with Yellow Border (Approved Permission), and Solid Red (Absent / LWP).", bullet_style))
    story.append(Paragraph("3. <b>Daily Work Log Submission:</b> Form allowing employees to submit projects worked on, tasks completed, hours spent, site location, and attach work verification photos.", bullet_style))
    story.append(Paragraph("4. <b>Leave & Permission Application:</b> Dynamic form supporting Casual Leave, Sick Leave, and Permission requests with real-time remaining-time duration validation (minimum 30 minutes, calculated strictly against the employee's remaining monthly permission quota with no arbitrary daily max or monthly request count limit).", bullet_style))
    story.append(Paragraph("5. <b>Assigned Daily Work Plans:</b> Dedicated table displaying tasks and schedules assigned by HR, with status badges (Assigned, In Progress, Completed).", bullet_style))
    story.append(Paragraph("6. <b>Direct HR Messaging:</b> Secure enquiry portal allowing staff to submit questions directly to the HR notification hub.", bullet_style))
    story.append(Paragraph("7. <b>Official Document Management:</b> Dedicated horizontal bar widget and modal enabling employees to submit or change their document at any time under strict privacy governance.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 6: HR OPERATIONS DASHBOARD
    # =========================================================================
    story.append(Paragraph("6. HR Operations Dashboard", h1_style))
    story.append(Paragraph(
        "The HR Dashboard (<code>templates/dashboard/hr_dashboard.html</code>) gives human resource managers full operational "
        "visibility and control over company attendance, employee records, leave approvals, and daily reporting.",
        body_style
    ))

    story.append(Paragraph("HR Dashboard Core Modules:", h2_style))
    story.append(Paragraph("• <b>Workforce KPI Metrics:</b> Cards summarizing Total Active Employees, Present Today, Absent Today, and Pending Leave Requests.", bullet_style))
    story.append(Paragraph("• <b>Horizontal Punch Strip:</b> Quick summary of the HR manager's personal punch-in, punch-out, work hours, and casual leave balance.", bullet_style))
    story.append(Paragraph("• <b>Staff Registry & Credentials Hub:</b> Displays all employees, codes, designations, departments, leave balances, and masked passwords. HR can toggle plain text passwords (<code>👁️</code>) or click <code>Edit Employee</code> to update details and passwords immediately.", bullet_style))
    story.append(Paragraph("• <b>Missing Punch-Out Correction Interface:</b> Dedicated table listing all employees who punched in but missed punch-out. HR enters the verified punch-out time and reason, immediately regularizing attendance with an immutable audit log.", bullet_style))
    story.append(Paragraph("• <b>Leave & Permission Review Modal:</b> Comprehensive approval queue. HR reviews reason, balance, and chooses classification (Paid Casual Leave, Paid Sick Leave, or Approved Permission) with zero salary deductions.", bullet_style))
    story.append(Paragraph("• <b>Official Office Holiday Modal:</b> Interface to declare corporate holidays, immediately updating employee calendars in green and applying full-day salary credit.", bullet_style))
    story.append(Paragraph("• <b>Hero Banner & Announcement Modal:</b> Allows HR to upload promotional banner graphics and corporate announcements displayed on the login page and dashboards.", bullet_style))
    story.append(Paragraph("• <b>Daily Work Plan Dispatcher:</b> HR can assign daily tasks and responsibilities to specific staff members with scheduled dates.", bullet_style))

    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 7: ADMIN DASHBOARD & SYSTEM GOVERNANCE
    # =========================================================================
    story.append(Paragraph("7. Admin Dashboard & System Governance", h1_style))
    story.append(Paragraph(
        "The Admin Dashboard (<code>templates/dashboard/admin_dashboard.html</code>) is restricted to executives and system administrators. "
        "It provides high-level organizational analytics, financial payroll summaries, and system configuration tools.",
        body_style
    ))
    story.append(Paragraph("Administrative Capabilities:", h2_style))
    story.append(Paragraph("• <b>Executive Analytics:</b> Total departments, active workforce count, daily presence percentage, and total monthly payroll expenditure.", bullet_style))
    story.append(Paragraph("• <b>Direct Django Admin Access:</b> Secure gateway link to <code>/django-admin/</code> for raw database table operations, group permissions, and low-level data inspection.", bullet_style))
    story.append(Paragraph("• <b>Administrative Leave Overrides:</b> Power to assign, adjust, or revoke leave and permission allocations for any employee directly.", bullet_style))
    story.append(Paragraph("• <b>Department & Designation Management:</b> Adding, renaming, or reassigning organizational units and staff hierarchies.", bullet_style))

    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 8: ATTENDANCE TRACKING, GPS & LIVE SELFIE
    # =========================================================================
    story.append(Paragraph("8. Attendance Tracking: GPS Location & Live Selfie Verification", h1_style))
    story.append(Paragraph(
        "Attendance verification in the Netcom Employee Management System Pro is strictly automated and tamper-proof. "
        "Both punch-in and punch-out are mandatory for every working day, requiring verified GPS location access and an HTML5 live camera frame snapshot.",
        body_style
    ))

    att_steps_data = [
        [Paragraph("<b>Step / Component</b>", table_header_style), Paragraph("<b>Client-Side Execution (Browser)</b>", table_header_style), Paragraph("<b>Server-Side Validation & Database Storage</b>", table_header_style)],
        [
            Paragraph("<b>1. GPS Location Acquisition</b>", table_cell_bold),
            Paragraph("Browser requests <code>navigator.geolocation.getCurrentPosition()</code> with high accuracy. Latitude and longitude are acquired and displayed in the status badge.", table_cell_style),
            Paragraph("Backend verifies coordinates are non-empty and non-zero. Formats reverse lookup coordinate string and stores in <code>in_latitude</code>, <code>in_longitude</code>, and <code>in_location</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>2. Live Camera Snapshot</b>", table_cell_bold),
            Paragraph("HTML5 MediaDevices activates video viewfinder. On punch click, an off-screen HTML5 Canvas draws the live video frame and exports a base64 DataURI image.", table_cell_style),
            Paragraph("Backend validates base64 integrity, converts it via <code>ContentFile</code> into a physical JPEG file, and stores it in <code>MEDIA_ROOT/attendance_photos/</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>3. Anti-Tamper Enforcement</b>", table_cell_bold),
            Paragraph("If GPS access is denied or camera is blocked, the frontend halts execution and alerts the user that both GPS and selfie are mandatory.", table_cell_style),
            Paragraph("If raw POST data lacks GPS coordinates or valid photo frame, backend returns an error message: <i>'Both GPS location access and a live selfie photo are mandatory.'</i>", table_cell_style)
        ],
        [
            Paragraph("<b>4. Duplicate Prevention</b>", table_cell_bold),
            Paragraph("Punch In button is automatically disabled once punch-in is recorded. Punch Out button is enabled only after punch-in exists.", table_cell_style),
            Paragraph("Backend enforces state logic: rejecting duplicate punch-ins if <code>in_time</code> exists, and rejecting punch-out if punch-in has not occurred.", table_cell_style)
        ],
    ]
    t_att = Table(att_steps_data, colWidths=[1.7 * inch, 2.6 * inch, 2.7 * inch])
    t_att.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_att)

    story.append(PageBreak())

    # =========================================================================
    # SECTION 9: WORKING HOURS, STATUS & MIDNIGHT RESET
    # =========================================================================
    story.append(Paragraph("9. Working Hours, Attendance Status & Midnight Evaluation", h1_style))
    story.append(Paragraph(
        "Attendance is calculated strictly based on the local calendar day from 12:00 AM to 11:59 PM. "
        "The system evaluates total active minutes between verified punch-in and punch-out times.",
        body_style
    ))

    rule_table = [
        [Paragraph("<b>Working Time Threshold</b>", table_header_style), Paragraph("<b>Computed Attendance Status</b>", table_header_style), Paragraph("<b>Salary Credit / Payroll Treatment</b>", table_header_style)],
        [Paragraph("<b>&ge; 9 Hours (540 Minutes)</b>", table_cell_bold), Paragraph("<font color='#059669'><b>Present</b> (Full Day)</font>", table_cell_style), Paragraph("<b>100% Full-Day Pay.</b> Zero deduction applied.", table_cell_style)],
        [Paragraph("<b>4h 30m to &lt; 9h (270–539 min)</b>", table_cell_bold), Paragraph("<font color='#d97706'><b>Half Day</b></font>", table_cell_style), Paragraph("<b>Half-Day Pay.</b> 0.5 day wage deducted from gross salary.", table_cell_style)],
        [Paragraph("<b>&lt; 4 Hours 30 Minutes</b>", table_cell_bold), Paragraph("<font color='#dc2626'><b>Absent</b></font>", table_cell_style), Paragraph("<b>Zero Pay.</b> 1.0 day wage deducted unless covered by approved permission or leave.", table_cell_style)],
        [Paragraph("<b>Approved 2-Hour Permission</b>", table_cell_bold), Paragraph("<font color='#2563eb'><b>Permission - 2 Hours</b></font>", table_cell_style), Paragraph("<b>Protected Full Credit.</b> Up to 2 hours credited towards working shift with zero deduction.", table_cell_style)],
        [Paragraph("<b>Official Office Duty</b>", table_cell_bold), Paragraph("<font color='#059669'><b>Present</b> (Official Duty)</font>", table_cell_style), Paragraph("<b>100% Full Credit.</b> Automatically marked Present with 0 deduction.", table_cell_style)],
        [Paragraph("<b>Approved Paid Leave</b>", table_cell_bold), Paragraph("<font color='#059669'><b>On Leave</b> (Paid)</font>", table_cell_style), Paragraph("<b>100% Full Credit.</b> Deducts 1 day from casual leave balance with 0 salary deduction.", table_cell_style)],
        [Paragraph("<b>Official Office Holiday</b>", table_cell_bold), Paragraph("<font color='#059669'><b>Office Holiday</b> (Paid)</font>", table_cell_style), Paragraph("<b>100% Full Credit.</b> Company-wide holiday with full wage credit.", table_cell_style)],
        [Paragraph("<b>Incomplete (Missing Punch-Out)</b>", table_cell_bold), Paragraph("<font color='#dc2626'><b>Missing Punch-Out / LWP</b></font>", table_cell_style), Paragraph("<b>Unfinalized / LWP.</b> Treated as Leave Without Pay by policy until verified by HR.", table_cell_style)],
    ]
    t_rules = Table(rule_table, colWidths=[2.2 * inch, 2.0 * inch, 2.8 * inch])
    t_rules.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_rules)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Automated 12:00 AM Midnight Evaluation Routine:", h2_style))
    story.append(Paragraph(
        "At the start of every new local calendar day (12:00 AM), the routine <code>reset_daily_missed_punch_in_status()</code> executes. "
        "It initializes the attendance state for the new day without deleting, clearing, or overwriting historical attendance records. "
        "Any employee who completed punch-in but neglected punch-out on a previous day has their record flagged for HR review.",
        body_style
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Dynamic Color-Coded Attendance Calendar & Sunday Policy:", h2_style))
    story.append(Paragraph(
        "The interactive attendance calendar embedded across Employee, HR, and Admin dashboards renders high-contrast, "
        "color-coded status indicators synchronized with the company attendance engine:",
        body_style
    ))

    cal_color_data = [
        [Paragraph("<b>Status / Event</b>", table_header_style), Paragraph("<b>Visual Styling & Border</b>", table_header_style), Paragraph("<b>Salary Credit & Attendance Rule</b>", table_header_style)],
        [
            Paragraph("<b>Full-Day Present (&ge; 9h)</b>", table_cell_bold),
            Paragraph("<font color='#16a34a'><b>Solid Green</b> (<code>#16a34a</code>)</font>", table_cell_style),
            Paragraph("100% full-day salary credit. Work time &ge; 540 minutes.", table_cell_style)
        ],
        [
            Paragraph("<b>Half-Day Present (4.5h to &lt;9h)</b>", table_cell_bold),
            Paragraph("<font color='#d97706'><b>Solid Yellow</b> (<code>#f59e0b</code>)</font>", table_cell_style),
            Paragraph("50% half-day salary credit. Work time between 270 and 539 minutes.", table_cell_style)
        ],
        [
            Paragraph("<b>Approved Permission</b>", table_cell_bold),
            Paragraph("<font color='#047857'><b>Green Fill + Yellow Border</b> (<code>3px solid #f59e0b</code>)</font>", table_cell_style),
            Paragraph("100% protected shift with ₹0.00 salary deduction. Deducts from monthly remaining permission balance.", table_cell_style)
        ],
        [
            Paragraph("<b>Missed Punch / Absent</b>", table_cell_bold),
            Paragraph("<font color='#ef4444'><b>Solid Red</b> (<code>#ef4444</code>)</font>", table_cell_style),
            Paragraph("Unpaid absence / missed punch-in or punch-out. 1.0 day deduction unless regularized by HR.", table_cell_style)
        ],
        [
            Paragraph("<b>Official Office Holiday</b>", table_cell_bold),
            Paragraph("<font color='#10b981'><b>Solid Green</b> (<code>#10b981</code>)</font>", table_cell_style),
            Paragraph("100% company-paid holiday with zero deduction and without reducing casual leave balance.", table_cell_style)
        ],
        [
            Paragraph("<b>Sunday Weekly Off (Paid)</b>", table_cell_bold),
            Paragraph("<font color='#10b981'><b>Solid Green</b> (<code>#10b981</code>)</font>", table_cell_style),
            Paragraph("Official paid weekly off with 100% full wage credit for employees in regular attendance.", table_cell_style)
        ],
        [
            Paragraph("<b>Sunday Sandwich / Continuous Absence</b>", table_cell_bold),
            Paragraph("<font color='#ef4444'><b>Solid Red</b> (<code>#ef4444</code>)</font>", table_cell_style),
            Paragraph("Enforces company sandwich rule: if continuous unapproved absence / LWP (up to 5 days including Sunday) occurs, Sunday automatically converts to unpaid LWP.", table_cell_style)
        ],
        [
            Paragraph("<b>Prior to Joining Date</b>", table_cell_bold),
            Paragraph("<b>Neutral Gray + Dashed Border</b> (<code>#f1f5f9</code>, <code>#cbd5e1</code>)", table_cell_style),
            Paragraph("Inactive non-working days prior to employee joining date. Strictly excluded from absence and salary deductions.", table_cell_style)
        ],
    ]
    t_cal_colors = Table(cal_color_data, colWidths=[2.2 * inch, 2.4 * inch, 2.4 * inch])
    t_cal_colors.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_cal_colors)
    story.append(Spacer(1, 8))
    story.append(Paragraph("• <b>Clean, High-Contrast Attendance Visualization:</b> High-contrast status colors and distinct borders provide immediate readability across Employee, HR, and Admin dashboards without requiring cluttered legend text containers.", bullet_style))

    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 10: LEAVE MANAGEMENT & CASUAL BALANCE RULES
    # =========================================================================
    story.append(Paragraph("10. Leave Management, Monthly Credit & Restoration Rules", h1_style))
    story.append(Paragraph(
        "The system enforces corporate attendance and leave governance with strict automated balance checks.",
        body_style
    ))
    story.append(Paragraph("Core Leave Governance Rules:", h2_style))
    story.append(Paragraph("1. <b>Strict Monthly Allowance (1 Day/Month):</b> On the 1st of every calendar month, active employees receive exactly 1 day of Casual Leave via <code>MonthlyLeaveCredit</code>.", bullet_style))
    story.append(Paragraph("2. <b>Strict Zero Carry-Forward Policy:</b> Unused casual leave from a prior month expires immediately at month-end. Unused leave does NOT accumulate or roll over.", bullet_style))
    story.append(Paragraph("3. <b>Automatic Casual Leave Restoration:</b> If an employee had a planned casual leave on a specific day, but subsequently reported to office and recorded valid attendance (&ge; 4.5 hours), the system cancels the leave and automatically restores the +1 day casual leave balance with an audit log.", bullet_style))
    story.append(Paragraph("4. <b>Leave Review Classification:</b> HR can classify requests as <b>Paid Casual Leave</b> (deducts 1d balance, full pay), <b>Paid Sick Leave</b> (full pay), or <b>Approved Permission</b> (no deduction).", bullet_style))
    story.append(Paragraph("5. <b>Monthly Permission Balance (Casual Leave Section):</b> In addition to full-day leaves, active staff receive a dedicated monthly permission quota of <b>5 hours</b> per calendar month with no daily maximum limit and no request count limit. The system calculates and enforces requests strictly against the remaining permission time, displayed prominently in the Casual Leave Balance stat card across Employee and HR dashboards.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 11: TWO-HOUR PERMISSION REQUEST WORKFLOW
    # =========================================================================
    story.append(Paragraph("11. Permission Request & Monthly Remaining Quota Workflow", h1_style))
    story.append(Paragraph(
        "To accommodate personal appointments, banking tasks, or medical consultations without penalizing staff with full-day or half-day salary deductions, "
        "the system features a dedicated <b>Permission</b> module integrated with a 5-hour monthly quota calculated strictly against remaining balance.",
        body_style
    ))

    perm_flow_data = [
        [Paragraph("<b>Workflow Phase</b>", table_header_style), Paragraph("<b>User Actions & Frontend Experience</b>", table_header_style), Paragraph("<b>Backend Rules & System Integration</b>", table_header_style)],
        [
            Paragraph("<b>1. Employee Selection</b>", table_cell_bold),
            Paragraph("Under Leave Category, employee selects <code>Permission</code>. Standard date range fields hide, revealing Permission Date, From Time, and To Time, alongside current remaining permission hours.", table_cell_style),
            Paragraph("Frontend dynamic script binds to time inputs. Computes duration in minutes in real-time.", table_cell_style)
        ],
        [
            Paragraph("<b>2. Live Validation & Guardrails</b>", table_cell_bold),
            Paragraph("Enforces policy limit: <b>Minimum 30 minutes</b>. Validates requested time strictly against remaining monthly permission balance. Eliminates arbitrary daily max and request count restrictions, allowing employees flexible scheduling within their quota.", table_cell_style),
            Paragraph("Backend validates: duration &ge; 30 minutes, requested hours &le; remaining balance. Rejects duplicate submissions for the same working day.", table_cell_style)
        ],
        [
            Paragraph("<b>3. HR Review & Approval</b>", table_cell_bold),
            Paragraph("Request appears in HR Leave Review queue with duration and times. HR clicks <code>Review & Decide</code>; modal auto-selects <code>Approved Permission</code>.", table_cell_style),
            Paragraph("Upon approval, backend sets <code>att.is_permission = True</code>, records permission hours, deducts approved duration from <code>MonthlyPermissionBalance.used_hours</code>, and logs an immutable audit trail.", table_cell_style)
        ],
        [
            Paragraph("<b>4. Attendance & Salary Credit</b>", table_cell_bold),
            Paragraph("Employee and HR dashboards immediately display green status with approved permission details and updated remaining balance.", table_cell_style),
            Paragraph("Payroll engine awards 100% full wage credit with <b>₹0.00 salary deduction</b> for the approved permission day.", table_cell_style)
        ],
    ]
    t_perm = Table(perm_flow_data, colWidths=[1.6 * inch, 2.7 * inch, 2.7 * inch])
    t_perm.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_perm)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Automated Monthly Permission Balance Reset Routine:", h2_style))
    story.append(Paragraph(
        "On the 1st of every calendar month, the routine <code>refresh_all_active_employees_monthly_permission()</code> executes. "
        "It resets the permission quota for all active employees to the full 5 hours. Unused permission hours do NOT roll over to the next month.",
        body_style
    ))

    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 12: OFFICE HOLIDAYS & CALENDAR SYNCHRONIZATION
    # =========================================================================
    story.append(Paragraph("12. Office Holidays & Corporate Calendar Synchronization", h1_style))
    story.append(Paragraph(
        "When an official holiday or non-working day is declared (such as festival holidays or corporate non-working days), "
        "authorized HR personnel select the date via the <b>Office Holiday Calendar</b> modal.",
        body_style
    ))
    story.append(Paragraph("Operational Synchronization Process:", h2_style))
    story.append(Paragraph("• <b>Bulk Workforce Synchronization:</b> Saving an <code>OfficePaidLeave</code> record automatically generates or updates attendance for all active employees on that date as <code>On Leave</code> with leave type <code>Paid Leave for the Office</code>.", bullet_style))
    story.append(Paragraph("• <b>Dashboard Holiday Banner:</b> On the holiday date, both Employee and HR dashboards display a prominent green banner: <i>'Official Office Holiday: [Title] (Approved Paid Leave)'</i>.", bullet_style))
    story.append(Paragraph("• <b>Protection from LWP:</b> Employees are guaranteed full-day salary credit without being flagged as Leave Without Pay (LWP) or Missed Punch-In.", bullet_style))

    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 13: DAILY WORK UPDATES & TASK PLANNING
    # =========================================================================
    story.append(Paragraph("13. Daily Work Updates & Task Planning", h1_style))
    story.append(Paragraph(
        "Staff accountability is reinforced through daily task reporting and HR task dispatching.",
        body_style
    ))
    story.append(Paragraph("Features:", h2_style))
    story.append(Paragraph("• <b>Daily Work Log Submission:</b> Employees enter project name, tasks accomplished, hours spent, and declare whether duty was on-site or off-site.", bullet_style))
    story.append(Paragraph("• <b>Off-Site Photographic Evidence:</b> For field or client-site visits, employees can upload photos. HR can view these attachments in an interactive lightbox modal.", bullet_style))
    story.append(Paragraph("• <b>HR Daily Work Planning:</b> HR can schedule tasks in advance via <code>DailyWorkPlan</code>. Staff view assigned duties directly on their dashboard under <i>My Assigned Daily Work Plans</i>.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 14: SALARY & PAYROLL CALCULATION ENGINE
    # =========================================================================
    story.append(Paragraph("14. Salary & Payroll Calculation Engine", h1_style))
    story.append(Paragraph(
        "The payroll engine implemented in <code>apps/payroll/views.py</code> calculates monthly employee compensation based on verified attendance data, working hours, and approved absences.",
        body_style
    ))

    story.append(Paragraph("Mathematical Formulas:", h2_style))
    story.append(Paragraph(
        "<b>1. Daily Wage Rate Calculation:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>Daily Rate = Gross Monthly Salary / Days in Calendar Month (28, 29, 30, or 31)</code>",
        body_style
    ))
    story.append(Paragraph(
        "<b>2. Attendance Deductions Formula:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>Attendance Deductions = (Half Days &times; 0.5 &times; Daily Rate) + (Absent Days &times; 1.0 &times; Daily Rate) + (Unpaid / LWP Days &times; 1.0 &times; Daily Rate)</code>",
        body_style
    ))
    story.append(Paragraph(
        "<b>3. Net Take-Home Salary:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>Net Salary = max(0, Gross Salary - (Statutory Deductions + Attendance Deductions))</code>",
        body_style
    ))

    story.append(Spacer(1, 6))

    payroll_sim_data = [
        [Paragraph("<b>Scenario Parameter</b>", table_header_style), Paragraph("<b>Sample Employee Value</b>", table_header_style), Paragraph("<b>Calculation & Salary Rule Applied</b>", table_header_style)],
        [Paragraph("<b>Monthly Gross Salary</b>", table_cell_bold), Paragraph("₹30,000.00", table_cell_style), Paragraph("Basic Salary + HRA + Allowances defined in SalaryStructure.", table_cell_style)],
        [Paragraph("<b>Days in Billing Month</b>", table_cell_bold), Paragraph("30 Days (e.g. November)", table_cell_style), Paragraph("Days in calendar month: calendar.monthrange(year, month)[1].", table_cell_style)],
        [Paragraph("<b>Derived Daily Wage Rate</b>", table_cell_bold), Paragraph("₹1,000.00 per day", table_cell_style), Paragraph("₹30,000 / 30 = ₹1,000.00 per day.", table_cell_style)],
        [Paragraph("<b>Full Days (&ge; 9 hours)</b>", table_cell_bold), Paragraph("24 Days", table_cell_style), Paragraph("100% pay credit = 24 &times; ₹1,000 = ₹24,000.00 (Zero deduction).", table_cell_style)],
        [Paragraph("<b>Approved Permission</b>", table_cell_bold), Paragraph("1 Day", table_cell_style), Paragraph("100% full wage credit = ₹1,000.00 (Zero salary deduction, protected shift).", table_cell_style)],
        [Paragraph("<b>Approved Casual Leave</b>", table_cell_bold), Paragraph("1 Day", table_cell_style), Paragraph("100% full wage credit = ₹1,000.00 (Deducts 1d from balance, 0 deduction).", table_cell_style)],
        [Paragraph("<b>Office Holidays (Declared)</b>", table_cell_bold), Paragraph("2 Days", table_cell_style), Paragraph("100% full wage credit = 2 &times; ₹1,000 = ₹2,000.00 (Zero deduction).", table_cell_style)],
        [Paragraph("<b>Half Days (4.5h to &lt;9h)</b>", table_cell_bold), Paragraph("1 Day (e.g. 5 hours worked)", table_cell_style), Paragraph("Deduction = 0.5 &times; ₹1,000.00 = <b>₹500.00 deduction</b>.", table_cell_style)],
        [Paragraph("<b>Unexcused Absence</b>", table_cell_bold), Paragraph("1 Day", table_cell_style), Paragraph("Deduction = 1.0 &times; ₹1,000.00 = <b>₹1,000.00 deduction</b>.", table_cell_style)],
        [Paragraph("<b>Total Monthly Deductions</b>", table_cell_bold), Paragraph("₹1,500.00", table_cell_style), Paragraph("₹500 (Half Day) + ₹1,000 (Absent) = ₹1,500.00.", table_cell_style)],
        [Paragraph("<b>Final Net Salary Disbursed</b>", table_cell_bold), Paragraph("<b>₹28,500.00</b>", table_cell_bold), Paragraph("Gross Salary (₹30,000) - Deductions (₹1,500) = <b>₹28,500.00</b>.", table_cell_style)],
    ]
    t_pay = Table(payroll_sim_data, colWidths=[2.0 * inch, 1.8 * inch, 3.2 * inch])
    t_pay.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_pay)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Special Payroll Calculation Rules:", h2_style))
    story.append(Paragraph("• <b>Joining Date Attendance Isolation:</b> Payroll strictly starts attendance calculations from <code>Employee.joining_date</code>. All dates prior to the official joining date are rendered inactive and excluded from absenteeism, missed punches, and salary deductions.", bullet_style))
    story.append(Paragraph("• <b>Sunday Weekly Off Credit & Sandwich Rule:</b> Sundays are credited with 100% full wage pay. If an employee incurs continuous unapproved absences encompassing Sunday (up to 5 continuous days including Sunday), the sandwich rule treats the Sunday as unpaid LWP and deducts 1 daily rate.", bullet_style))
    story.append(Paragraph("• <b>Permission Shift Protection:</b> Approved permission (within the monthly 5-hour quota) carries 100% full wage credit with ₹0.00 salary deduction.", bullet_style))

    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 15: REPORTING, EXPORTS, BACKUP & RESTORATION
    # =========================================================================
    story.append(Paragraph("15. Reporting, Analytics, Excel & PDF Exports", h1_style))
    story.append(Paragraph(
        "The system includes an export engine supporting both formatted Excel spreadsheets (<code>.xlsx</code>) "
        "and styled PDF reports (<code>.pdf</code>) for auditing, compliance, and accounting.",
        body_style
    ))
    story.append(Paragraph("Export Capabilities:", h2_style))
    story.append(Paragraph("• <b>Excel Workforce Export:</b> Built with <code>openpyxl</code>. Generates multi-tab workbooks containing employee rosters, daily punch timestamps, GPS locations, leave history, and payroll registers.", bullet_style))
    story.append(Paragraph("• <b>Corporate PDF Analytics:</b> Built with <code>reportlab</code>. Generates branded PDF reports featuring employee metrics, department presence percentages, and audit logs.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 16: SECURITY, ERROR HANDLING & RESILIENCE
    # =========================================================================
    story.append(Paragraph("16. Security, Error Handling & System Resilience", h1_style))
    story.append(Paragraph(
        "The application incorporates multiple layers of security to defend against common web vulnerabilities "
        "and maintain operational integrity.",
        body_style
    ))

    sec_data = [
        [Paragraph("<b>Security / Resilience Area</b>", table_header_style), Paragraph("<b>Implementation Mechanism</b>", table_header_style), Paragraph("<b>Operational Benefit & Protection</b>", table_header_style)],
        [
            Paragraph("<b>Cross-Site Request Forgery</b>", table_cell_bold),
            Paragraph("Django <code>{% csrf_token %}</code> tokens enforced on all POST endpoints.", table_cell_style),
            Paragraph("Prevents unauthorized commands from malicious third-party websites.", table_cell_style)
        ],
        [
            Paragraph("<b>SQL Injection Protection</b>", table_cell_bold),
            Paragraph("Django ORM parameterized query construction.", table_cell_style),
            Paragraph("All queries use parameterized inputs; raw unescaped SQL execution is prohibited.", table_cell_style)
        ],
        [
            Paragraph("<b>Role Access Escalation</b>", table_cell_bold),
            Paragraph("Custom decorators: <code>@admin_required</code> and <code>@hr_or_admin_required</code>.", table_cell_style),
            Paragraph("Prevents unauthorized employees from tampering with management functions or viewing peers' data.", table_cell_style)
        ],
        [
            Paragraph("<b>Missing Punch-Out Protection</b>", table_cell_bold),
            Paragraph("Incomplete attendance cannot finalize working hours until reviewed by HR.", table_cell_style),
            Paragraph("Prevents inflated or arbitrary salary credit for incomplete punch records.", table_cell_style)
        ],
        [
            Paragraph("<b>Camera & GPS Permission Handling</b>", table_cell_bold),
            Paragraph("JavaScript defensive checks with fallback alert notifications.", table_cell_style),
            Paragraph("Displays user-friendly browser permission instructions if camera or GPS is blocked.", table_cell_style)
        ],
    ]
    t_sec = Table(sec_data, colWidths=[1.8 * inch, 2.4 * inch, 2.8 * inch])
    t_sec.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_sec)

    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 17: BACKUP, RESTORATION & DEPLOYMENT GUIDE
    # =========================================================================
    story.append(Paragraph("17. Database Backup, Restoration & Deployment Guide", h1_style))
    story.append(Paragraph(
        "Standard operating procedures for database maintenance, backup, restoration, and cloud deployment.",
        body_style
    ))

    story.append(Paragraph("17.1 Database Backup Procedures:", h2_style))
    story.append(Paragraph(
        "<b>A. Django Application-Level Fixture Backup:</b><br/>"
        "<code>python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > database/backup_snapshot.json</code>",
        code_style
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>B. MySQL Native Database Backup:</b><br/>"
        "<code>mysqldump -u [db_user] -p[db_password] -h [db_host] [db_name] > backup_netcom_db.sql</code>",
        code_style
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("17.2 Database Restoration Procedures:", h2_style))
    story.append(Paragraph(
        "<b>A. Restoring from Django Fixture:</b><br/>"
        "<code>python manage.py migrate</code><br/>"
        "<code>python manage.py loaddata database/backup_snapshot.json</code>",
        code_style
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>B. Restoring from MySQL Dump:</b><br/>"
        "<code>mysql -u [db_user] -p[db_password] -h [db_host] [db_name] < backup_netcom_db.sql</code>",
        code_style
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("17.3 Cloud Production Deployment Instructions (e.g. Railway / Linux VPS):", h2_style))
    story.append(Paragraph("1. <b>Repository Cloning:</b> Clone project repository and ensure Python 3.12+ is installed.", bullet_style))
    story.append(Paragraph("2. <b>Virtual Environment & Dependencies:</b> Install requirements: <code>pip install -r requirements.txt</code>.", bullet_style))
    story.append(Paragraph("3. <b>Environment Variables Configuration:</b> Set <code>SECRET_KEY</code>, <code>DEBUG=False</code>, <code>ALLOWED_HOSTS</code>, and <code>DATABASE_URL</code>.", bullet_style))
    story.append(Paragraph("4. <b>Static File Collection:</b> Execute <code>python manage.py collectstatic --noinput</code> for WhiteNoise asset serving.", bullet_style))
    story.append(Paragraph("5. <b>Database Migrations & Seed:</b> Execute <code>python manage.py migrate</code> followed by <code>python manage.py init_production_data</code> to seed initial credentials and verified roles.", bullet_style))
    story.append(Paragraph("6. <b>WSGI Server Process:</b> Launch with Gunicorn: <code>gunicorn config.wsgi:application --bind 0.0.0.0:$PORT</code>.", bullet_style))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1, color=c_primary, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "<b>End of Technical & Operational Documentation</b> • Netcom Computers Pvt Ltd • Confidential",
        ParagraphStyle('EndFooter', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=c_muted, alignment=1)
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Documentation PDF successfully generated: {filename}")


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else "Netcom_Employee_Management_System_Documentation.pdf"
    build_documentation_pdf(target)
