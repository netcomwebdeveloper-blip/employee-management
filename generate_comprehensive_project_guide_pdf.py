import os
import sys
import calendar
from datetime import datetime

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
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#475569"))

        # Running Header (Skip on Cover Page)
        if self._pageNumber > 1:
            self.drawString(45, 11 * inch - 30, "NETCOM COMPUTERS PVT LTD — Project Creation, Architecture, Code & Developer Reference Guide")
            self.drawRightString(8.5 * inch - 45, 11 * inch - 30, "Python • Django • SQL • HTML • CSS • JS")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(45, 11 * inch - 34, 8.5 * inch - 45, 11 * inch - 34)

        # Running Footer (All Pages)
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 45, 24, footer_text)
        self.drawString(45, 24, "Netcom Computers Pvt Ltd • Confidential • System Architecture & Developer Manual")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(45, 34, 8.5 * inch - 45, 34)
        self.restoreState()


def build_pdf(filename="Netcom_Complete_Code_Architecture_and_Developer_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=42,
        bottomMargin=42
    )

    styles = getSampleStyleSheet()

    c_primary = colors.HexColor("#1e3a8a")     # Deep corporate navy blue
    c_secondary = colors.HexColor("#0284c7")   # Tech blue
    c_dark = colors.HexColor("#0f172a")        # Slate text
    c_muted = colors.HexColor("#475569")       # Muted slate
    c_border = colors.HexColor("#cbd5e1")      # Border gray
    c_light_bg = colors.HexColor("#f8fafc")    # Off-white / light slate
    c_code_bg = colors.HexColor("#f1f5f9")     # Code snippet background
    c_accent = colors.HexColor("#4338ca")      # Indigo accent
    c_success = colors.HexColor("#047857")     # Green
    c_warning = colors.HexColor("#b45309")     # Amber
    c_highlight = colors.HexColor("#fef3c7")   # Light amber

    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=21,
        leading=26,
        textColor=c_primary,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14.5,
        textColor=c_muted,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=c_primary,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13.5,
        textColor=c_secondary,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=c_dark,
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=c_dark,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=6.8,
        leading=8.8,
        textColor=colors.HexColor("#0f172a"),
        backColor=c_code_bg,
        borderPadding=3,
        spaceBefore=2,
        spaceAfter=3
    )

    code_title_style = ParagraphStyle(
        'CodeTitle',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=7.2,
        leading=9.5,
        textColor=c_primary,
        spaceBefore=4,
        spaceAfter=1
    )

    table_header_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
        alignment=0
    )

    table_cell_style = ParagraphStyle(
        'TC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9.5,
        textColor=c_dark
    )

    table_cell_bold = ParagraphStyle(
        'TCB',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9.5,
        textColor=c_dark
    )

    story = []

    # =========================================================================
    # COVER / HEADER BANNER
    # =========================================================================
    story.append(Paragraph("NETCOM COMPUTERS PVT LTD • SOFTWARE ENGINEERING DIVISION", ParagraphStyle('CompanyPre', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=c_secondary, textTransform='uppercase', spaceAfter=3)))
    story.append(Paragraph("Enterprise Employee Management System Pro", title_style))
    story.append(Paragraph("Complete Technical Guide: Tools, Creation Workflow, Architecture, Functions & Methods, SQL, Django, Python, HTML5, CSS3 & JavaScript", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=c_primary, spaceBefore=0, spaceAfter=8))

    # Meta Overview Card
    overview_data = [
        [
            Paragraph("<b>Project Framework:</b> Django 5.0.6 (MVT Architecture)", table_cell_style),
            Paragraph("<b>Core Language:</b> Python 3.12+ (OOP & Clean Code)", table_cell_style),
            Paragraph("<b>Database:</b> MySQL 8.0 & SQLite3 Multi-Engine", table_cell_style)
        ],
        [
            Paragraph("<b>Frontend:</b> Semantic HTML5 + CSS3 + ES6 JS", table_cell_style),
            Paragraph("<b>Client APIs:</b> WebRTC MediaDevices & W3C GPS", table_cell_style),
            Paragraph("<b>Documents:</b> ReportLab (PDF) & OpenPyXL (Excel)", table_cell_style)
        ],
        [
            Paragraph("<b>Application Host:</b> http://127.0.0.1:8000/login/", table_cell_style),
            Paragraph("<b>Admin Credentials:</b> NETCOM / Netcom@2026@Netcom", table_cell_style),
            Paragraph("<b>Scope:</b> HRMS, Attendance, Leave, Payroll, Audit", table_cell_style)
        ]
    ]
    t_over = Table(overview_data, colWidths=[175, 175, 172])
    t_over.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_light_bg),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_over)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 1: REQUIRED TOOLS & ENVIRONMENT TO CREATE THIS PROJECT
    # =========================================================================
    story.append(Paragraph("1. Development Tools & Software Environment", h1_style))
    story.append(Paragraph(
        "To build, develop, and run this enterprise employee management system from scratch, the following toolchain and software ecosystem are utilized:",
        body_style
    ))

    tools_data = [
        [Paragraph("Tool / Component", table_header_style), Paragraph("Category / Version", table_header_style), Paragraph("Exact Role & Implementation Purpose in Project", table_header_style)],
        [
            Paragraph("<b>Python 3.12+</b>", table_cell_bold),
            Paragraph("Programming Runtime", table_cell_style),
            Paragraph("Core programming language powering the backend, data structures, date/time calculations, ORM logic, decorators, and file handling.", table_cell_style)
        ],
        [
            Paragraph("<b>Django 5.0.6</b>", table_cell_bold),
            Paragraph("Full-Stack Web Framework", table_cell_style),
            Paragraph("Provides Model-View-Template (MVT) architecture, URL routing, ORM database engine, session auth, CSRF protection, and admin governance.", table_cell_style)
        ],
        [
            Paragraph("<b>MySQL 8.0 / SQLite</b>", table_cell_bold),
            Paragraph("Relational Database", table_cell_style),
            Paragraph("ACID-compliant storage for users, staff records, attendance photos/GPS, leaves, and payroll records. SQLite is used for zero-config testing.", table_cell_style)
        ],
        [
            Paragraph("<b>ReportLab 5.0.1</b>", table_cell_bold),
            Paragraph("PDF Generation Engine", table_cell_style),
            Paragraph("Programmatic vector PDF compilation for official documentation, employee dossiers, and attendance reports with headers and page counts.", table_cell_style)
        ],
        [
            Paragraph("<b>OpenPyXL</b>", table_cell_bold),
            Paragraph("Excel Generation Engine", table_cell_style),
            Paragraph("Generates structured, multi-sheet corporate <code>.xlsx</code> spreadsheets with styled table headers, thin borders, and numeric formatting.", table_cell_style)
        ],
        [
            Paragraph("<b>Pillow (PIL)</b>", table_cell_bold),
            Paragraph("Image Processing", table_cell_style),
            Paragraph("Validates, resizes, and processes employee profile photos, attendance verification selfies, banners, and offsite work proofs.", table_cell_style)
        ],
        [
            Paragraph("<b>WhiteNoise & Gunicorn</b>", table_cell_bold),
            Paragraph("WSGI Server & Static Asset Host", table_cell_style),
            Paragraph("Gunicorn serves concurrent WSGI HTTP workers in production; WhiteNoise enables direct, high-speed static asset caching without Nginx.", table_cell_style)
        ],
        [
            Paragraph("<b>Modern Web Browser</b>", table_cell_bold),
            Paragraph("Chrome / Edge / Firefox", table_cell_style),
            Paragraph("Provides runtime client APIs: <code>navigator.mediaDevices.getUserMedia()</code> (Camera) and <code>navigator.geolocation</code> (GPS).", table_cell_style)
        ],
    ]
    t_tools = Table(tools_data, colWidths=[105, 115, 302])
    t_tools.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('PADDING', (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_tools)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 2: STEP-BY-STEP PROJECT CREATION WORKFLOW (FROM SCRATCH)
    # =========================================================================
    story.append(Paragraph("2. Step-by-Step Project Creation Workflow", h1_style))
    story.append(Paragraph(
        "Follow these exact sequential steps and terminal commands to create and configure the entire codebase from scratch:",
        body_style
    ))

    create_steps = [
        ("Step 1: Environment & Virtualenv Setup",
         "mkdir employee_management && cd employee_management\n"
         "python -m venv venv\n"
         "# Windows activation: venv\\Scripts\\activate  |  Linux/Mac: source venv/bin/activate"),

        ("Step 2: Install Required Dependencies",
         "pip install django==5.0.6 reportlab==5.0.1 openpyxl pillow whitenoise gunicorn mysqlclient python-dotenv\n"
         "pip freeze > requirements.txt"),

        ("Step 3: Initialize Django Project & Modular Apps",
         "django-admin startproject config .\n"
         "python manage.py startapp apps/employees\n"
         "python manage.py startapp apps/departments\n"
         "python manage.py startapp apps/attendance\n"
         "python manage.py startapp apps/leave_management\n"
         "python manage.py startapp apps/payroll\n"
         "python manage.py startapp apps/dashboard\n"
         "python manage.py startapp apps/reports\n"
         "python manage.py startapp apps/users"),

        ("Step 4: Configure config/settings.py",
         "# In INSTALLED_APPS add: 'apps.users', 'apps.employees', 'apps.departments',\n"
         "# 'apps.attendance', 'apps.leave_management', 'apps.payroll', 'apps.dashboard', 'apps.reports'\n"
         "# Configure TEMPLATES DIRS: [BASE_DIR / 'templates']\n"
         "# Configure STATIC_URL = '/static/', STATICFILES_DIRS = [BASE_DIR / 'static'], STATIC_ROOT = BASE_DIR / 'staticfiles'\n"
         "# Configure MEDIA_URL = '/media/', MEDIA_ROOT = BASE_DIR / 'media'"),

        ("Step 5: Database Migrations & Initial Setup",
         "python manage.py makemigrations users employees departments attendance leave_management payroll dashboard\n"
         "python manage.py migrate\n"
         "python manage.py createsuperuser  # Create main Admin account"),

        ("Step 6: Launch Development Server",
         "python manage.py runserver 0.0.0.0:8000\n"
         "# Navigate browser to: http://127.0.0.1:8000/login/")
    ]

    for title, code in create_steps:
        story.append(Paragraph(f"• <b>{title}</b>", ParagraphStyle('StepTitle', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=c_primary)))
        story.append(Paragraph(code.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 3: SQL RELATIONAL DATABASE SCHEMA & ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("3. Relational Database Design & SQL Architecture", h1_style))
    story.append(Paragraph(
        "The system utilizes a fully normalized relational schema with primary keys, foreign key constraints with <code>CASCADE</code> rules, "
        "unique composite indexes, and strict data typing. Below are the key SQL tables, DDL structures, and relationships:",
        body_style
    ))

    sql_schema_data = [
        [Paragraph("SQL Table Name", table_header_style), Paragraph("Key Columns & Data Types", table_header_style), Paragraph("Constraints & Relational Purpose", table_header_style)],
        [
            Paragraph("<b>auth_user</b><br/><i>(Django Core)</i>", table_cell_bold),
            Paragraph("<code>id INT AUTO_INCREMENT PRIMARY KEY<br/>username VARCHAR(150) UNIQUE<br/>password VARCHAR(128)<br/>first_name, last_name, email<br/>is_staff, is_superuser, is_active</code>", table_cell_style),
            Paragraph("Central identity table. Uses PBKDF2 SHA256 hashed passwords and session authentication tokens.", table_cell_style)
        ],
        [
            Paragraph("<b>employees_employee</b>", table_cell_bold),
            Paragraph("<code>id INT AUTO_INCREMENT PRIMARY KEY<br/>user_id INT UNIQUE (FK auth_user)<br/>employee_code VARCHAR(20) UNIQUE<br/>role VARCHAR(20) [ADMIN, HR, EMPLOYEE]<br/>joining_date DATE NOT NULL<br/>phone VARCHAR(15), basic_salary DECIMAL(10,2)<br/>casual_leave_balance INT DEFAULT 1<br/>raw_password VARCHAR(128)<br/>profile_picture VARCHAR(100), document VARCHAR(100)</code>", table_cell_style),
            Paragraph("One-to-One extension of <code>auth_user</code>. Mandatory <code>joining_date</code> isolates calendar and attendance calculations.", table_cell_style)
        ],
        [
            Paragraph("<b>attendance_attendance</b>", table_cell_bold),
            Paragraph("<code>id INT AUTO_INCREMENT PRIMARY KEY<br/>employee_id INT (FK employees_employee)<br/>date DATE NOT NULL<br/>in_time TIME, out_time TIME<br/>status VARCHAR(20) [Present, Half Day, Absent]<br/>in_photo VARCHAR(255), out_photo VARCHAR(255)<br/>in_latitude DECIMAL(9,6), in_longitude DECIMAL(9,6)<br/>total_work_minutes INT DEFAULT 0<br/>is_permission BOOLEAN, permission_hours DECIMAL(4,2)</code>", table_cell_style),
            Paragraph("<b>UNIQUE KEY (employee_id, date)</b>. Strictly enforces single daily punch session with photo and GPS tracking.", table_cell_style)
        ],
        [
            Paragraph("<b>attendance_attendanceauditlog</b>", table_cell_bold),
            Paragraph("<code>id INT AUTO_INCREMENT PRIMARY KEY<br/>attendance_id INT (FK attendance_attendance)<br/>changed_by_id INT (FK auth_user)<br/>action VARCHAR(50), timestamp DATETIME<br/>old_values JSON/TEXT, new_values JSON/TEXT<br/>ip_address VARCHAR(45)</code>", table_cell_style),
            Paragraph("Immutable audit trail tracking every manual override, missing punch correction, and administrative adjustment.", table_cell_style)
        ],
        [
            Paragraph("<b>leave_management_leaverequest</b>", table_cell_bold),
            Paragraph("<code>id INT AUTO_INCREMENT PRIMARY KEY<br/>employee_id INT (FK employees_employee)<br/>leave_type VARCHAR(20) [Casual, Sick, LWP, Permission]<br/>from_date DATE, to_date DATE, total_days INT<br/>status VARCHAR(20) [Pending, Approved, Rejected]<br/>reason TEXT, is_paid BOOLEAN, reviewed_by_id INT</code>", table_cell_style),
            Paragraph("Leave applications and 2-hour permission submissions. Approved paid leaves credit attendance with zero salary deduction.", table_cell_style)
        ],
        [
            Paragraph("<b>leave_management_monthlyleavecredit</b>", table_cell_bold),
            Paragraph("<code>id INT AUTO_INCREMENT PRIMARY KEY<br/>employee_id INT (FK employees_employee)<br/>year INT, month INT, casual_added INT DEFAULT 1<br/>created_at DATETIME</code>", table_cell_style),
            Paragraph("<b>UNIQUE KEY (employee_id, year, month)</b>. Strictly enforces the company rule of 1 casual leave credit per month without rollover.", table_cell_style)
        ],
        [
            Paragraph("<b>payroll_salarystructure</b>", table_cell_bold),
            Paragraph("<code>id INT AUTO_INCREMENT PRIMARY KEY<br/>employee_id INT UNIQUE (FK employees_employee)<br/>basic_salary DECIMAL(10,2)<br/>hra DECIMAL(10,2), allowances DECIMAL(10,2)<br/>statutory_deductions DECIMAL(10,2)</code>", table_cell_style),
            Paragraph("Base salary blueprint for each staff member. Gross Salary = Basic + HRA + Allowances.", table_cell_style)
        ],
        [
            Paragraph("<b>payroll_payrollrecord</b>", table_cell_bold),
            Paragraph("<code>id INT AUTO_INCREMENT PRIMARY KEY<br/>employee_id INT (FK employees_employee)<br/>year INT, month INT, gross_salary DECIMAL(10,2)<br/>attendance_deductions DECIMAL(10,2)<br/>net_salary DECIMAL(10,2), status VARCHAR(20)</code>", table_cell_style),
            Paragraph("<b>UNIQUE KEY (employee_id, year, month)</b>. Monthly payslip record with computed daily rates and attendance deductions.", table_cell_style)
        ],
    ]
    t_sql = Table(sql_schema_data, colWidths=[115, 230, 177])
    t_sql.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_sql)
    story.append(Spacer(1, 4))

    story.append(Paragraph("SQL DDL & ORM Query Translation Examples:", h2_style))
    sample_sql = (
        "-- 1. SQL DDL Table Creation for Attendance Record\n"
        "CREATE TABLE attendance_attendance (\n"
        "    id INT AUTO_INCREMENT PRIMARY KEY,\n"
        "    employee_id INT NOT NULL,\n"
        "    date DATE NOT NULL,\n"
        "    in_time TIME NULL, out_time TIME NULL,\n"
        "    status VARCHAR(20) NOT NULL DEFAULT 'Present',\n"
        "    in_photo VARCHAR(255) NULL, out_photo VARCHAR(255) NULL,\n"
        "    in_latitude DECIMAL(9,6) NULL, in_longitude DECIMAL(9,6) NULL,\n"
        "    total_work_minutes INT NOT NULL DEFAULT 0,\n"
        "    CONSTRAINT fk_attendance_employee FOREIGN KEY (employee_id) REFERENCES employees_employee(id) ON DELETE CASCADE,\n"
        "    CONSTRAINT uq_attendance_emp_date UNIQUE (employee_id, date)\n"
        ");\n\n"
        "-- 2. Equivalent High-Performance Django ORM Query with Joins:\n"
        "qs = Attendance.objects.filter(date__year=2026, date__month=10).select_related('employee__user', 'employee__department') \\\n"
        "        .annotate(total_punches=Count('id')).order_by('-date')"
    )
    story.append(Paragraph(sample_sql.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 4: PYTHON & DJANGO FUNCTIONS AND METHODS
    # =========================================================================
    story.append(Paragraph("4. Backend Architecture: Python & Django Functions and Methods", h1_style))
    story.append(Paragraph(
        "Every core application module contains dedicated function-based views (FBVs), model methods, custom decorators, "
        "and business logic routines. Below is the comprehensive technical catalog of all major functions and methods:",
        body_style
    ))

    fn_catalog_data = [
        [Paragraph("Module / App", table_header_style), Paragraph("Function / Method Signature", table_header_style), Paragraph("Parameters, Internal Algorithm & Return Value", table_header_style)],
        
        # Users & Auth
        [
            Paragraph("<b>apps.users</b><br/><i>Authentication</i>", table_cell_bold),
            Paragraph("<code>login_view(request)</code>", table_cell_style),
            Paragraph("<b>Args:</b> <code>request</code> (POST/GET).<br/><b>Logic:</b> Validates credentials via <code>authenticate()</code>. If valid, logs user in via <code>login()</code> and routes dynamically to <code>/dashboard/</code> based on role (Admin, HR, Employee).<br/><b>Returns:</b> HTTP 302 Redirect or rendered <code>users/login.html</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.users</b><br/><i>Authentication</i>", table_cell_bold),
            Paragraph("<code>logout_view(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Calls <code>request.session.flush()</code> and <code>django.contrib.auth.logout()</code>, invalidating user session cookies to prevent session hijacking.<br/><b>Returns:</b> Redirects to <code>/login/</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.users</b><br/><i>User Profile</i>", table_cell_bold),
            Paragraph("<code>user_profile_view(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Allows users to view profile, upload avatar and documents. If password is changed, updates both Django password hash and <code>employee.raw_password</code> for HR visibility.<br/><b>Returns:</b> Rendered <code>users/profile.html</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.users</b><br/><i>Security Decorator</i>", table_cell_bold),
            Paragraph("<code>@admin_required</code><br/><code>@hr_or_admin_required</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Inspects <code>request.user.employee.role</code> and <code>is_superuser</code>. Raises <code>PermissionDenied</code> (HTTP 403) or redirects to login if user lacks authorization.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.users</b><br/><i>Self-Healing</i>", table_cell_bold),
            Paragraph("<code>get_or_create_employee_profile(user)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Auto-creates or heals an <code>Employee</code> profile for users lacking one, mapping superusers to <code>ADMIN</code> and 'hr' users to <code>HR</code> role automatically.", table_cell_style)
        ],

        # Employees App
        [
            Paragraph("<b>apps.employees</b><br/><i>Workforce Master</i>", table_cell_bold),
            Paragraph("<code>employee_create(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Creates <code>auth_user</code>, generates unique <code>employee_code</code>, assigns department/designation, captures mandatory <code>joining_date</code>, and saves initial salary and raw password.<br/><b>Returns:</b> Redirect to staff directory.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.employees</b><br/><i>Workforce Master</i>", table_cell_bold),
            Paragraph("<code>quick_edit_joining_date(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> AJAX/POST endpoint allowing HR/Admin to immediately update <code>Employee.joining_date</code>. Triggers automatic refresh of active attendance calendars and payroll calculations.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.employees</b><br/><i>Model Method</i>", table_cell_bold),
            Paragraph("<code>Employee.is_eligible_for_date(date)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Evaluates if <code>date &gt;= self.joining_date</code>. Returns <code>False</code> for prior dates, isolating pre-joining days from absenteeism, missed punch penalties, and salary cuts.", table_cell_style)
        ],

        # Attendance App
        [
            Paragraph("<b>apps.attendance</b><br/><i>Duty Punch</i>", table_cell_bold),
            Paragraph("<code>punch_in(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Decodes Base64 live selfie camera photo, captures W3C GPS latitude/longitude, verifies once-per-day rule, and creates <code>Attendance</code> record with <code>in_time=now()</code>.<br/><b>Returns:</b> JSON success response.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.attendance</b><br/><i>Duty Punch</i>", table_cell_bold),
            Paragraph("<code>punch_out(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Saves exit webcam selfie photo, records <code>out_time</code>, calculates <code>total_work_minutes</code>, and evaluates status: <b>Present (&ge;9h)</b>, <b>Half Day (4.5h&ndash;9h)</b>, or <b>Absent (&lt;4.5h)</b>.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.attendance</b><br/><i>Governance</i>", table_cell_bold),
            Paragraph("<code>attendance_override(request, attendance_id)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Allows HR/Admin to adjust punch times and status. Automatically logs old vs new values, user ID, timestamp, and IP address into <code>AttendanceAuditLog</code> for compliance.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.attendance</b><br/><i>Task Log</i>", table_cell_bold),
            Paragraph("<code>daily_work_submit(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Captures employee's completed tasks, hours worked, on-site/off-site flag, and optional off-site photo proof into <code>DailyWork</code>.<br/><b>Returns:</b> Redirect to dashboard.", table_cell_style)
        ],

        # Leave Management App
        [
            Paragraph("<b>apps.leave_management</b><br/><i>Leave Workflow</i>", table_cell_bold),
            Paragraph("<code>apply_leave(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Validates dates, checks available <code>casual_leave_balance</code>, prevents overlapping requests, and creates <code>LeaveRequest</code> with <code>status='Pending'</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.leave_management</b><br/><i>Leave Review</i>", table_cell_bold),
            Paragraph("<code>review_leave(request, leave_id)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> HR approves or rejects leave. If approved as Paid Casual Leave, deducts 1 day from balance and syncs calendar with full wage credit (zero salary deduction).", table_cell_style)
        ],
        [
            Paragraph("<b>apps.leave_management</b><br/><i>Permission Workflow</i>", table_cell_bold),
            Paragraph("<code>permission_request(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Validates sub-day 2-hour permission requests against monthly 5-hour quota. Prevents exceeding balance and sends request to HR review queue.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.leave_management</b><br/><i>Quota Engine</i>", table_cell_bold),
            Paragraph("<code>credit_monthly_casual_leave()</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Automated 1st of month cron/signal routine that credits exactly 1 casual leave to active employees, enforcing non-cumulative zero-rollover policy.", table_cell_style)
        ],

        # Payroll App
        [
            Paragraph("<b>apps.payroll</b><br/><i>Payroll Engine</i>", table_cell_bold),
            Paragraph("<code>calculate_daily_rate(gross, year, month)</code>", table_cell_style),
            Paragraph("<b>Formula:</b> <code>gross_salary / calendar.monthrange(year, month)[1]</code>.<br/>Calculates the exact daily rate based on total calendar days in billing month (28, 29, 30, or 31).", table_cell_style)
        ],
        [
            Paragraph("<b>apps.payroll</b><br/><i>Payroll Engine</i>", table_cell_bold),
            Paragraph("<code>calculate_attendance_deductions(emp, year, month)</code>", table_cell_style),
            Paragraph("<b>Formula:</b> <code>(half_days &times; 0.5 &times; rate) + (absent_days &times; 1.0 &times; rate) + (sandwich_days &times; 1.0 &times; rate)</code>.<br/>Excludes dates before joining date and approved permissions.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.payroll</b><br/><i>Batch Generation</i>", table_cell_bold),
            Paragraph("<code>generate_monthly_payroll(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Iterates through all active staff, computes attendance deductions, derives Net Salary = Gross - Deductions, and persists records in <code>PayrollRecord</code>.", table_cell_style)
        ],

        # Reports & Dashboard
        [
            Paragraph("<b>apps.reports</b><br/><i>Export Engine</i>", table_cell_bold),
            Paragraph("<code>export_attendance_excel(request)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Uses <code>openpyxl</code> to build styled Excel spreadsheets with headers, borders, and date filters.<br/><b>Returns:</b> <code>application/vnd.openxmlformats-officedocument.spreadsheetml.sheet</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>apps.reports</b><br/><i>Export Engine</i>", table_cell_bold),
            Paragraph("<code>export_dossier_pdf(request, emp_id)</code>", table_cell_style),
            Paragraph("<b>Logic:</b> Uses <code>reportlab</code> to generate complete executive employee dossiers with embedded avatar, attendance history, and leave stats.<br/><b>Returns:</b> <code>application/pdf</code>.", table_cell_style)
        ],
    ]

    t_fn = Table(fn_catalog_data, colWidths=[105, 145, 272])
    t_fn.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_fn)

    story.append(PageBreak())

    # =========================================================================
    # SECTION 5: FRONTEND TECHNOLOGIES: HTML5, CSS3 & JAVASCRIPT (ES6+)
    # =========================================================================
    story.append(Paragraph("5. Frontend Architecture: HTML5, CSS3 & JavaScript (ES6+)", h1_style))
    story.append(Paragraph(
        "The user presentation layer is built without heavyweight JavaScript frameworks, utilizing modern semantic HTML5, "
        "a modular custom CSS3 design system, and vanilla ES6+ JavaScript for hardware camera access and GPS positioning.",
        body_style
    ))

    # HTML5 Sub-section
    story.append(Paragraph("5.1 Semantic HTML5 & Django Template Language (DTL)", h2_style))
    story.append(Paragraph(
        "• <b>Base Template Inheritance:</b> All templates extend <code>templates/base.html</code> using Django's <code>{% extends 'base.html' %}</code> and <code>{% block content %}</code>.<br/>"
        "• <b>Global Context Injection:</b> Banners, branding logo, announcement popups, and user role badges are injected globally across all views via custom context processors.<br/>"
        "• <b>Hardware Viewfinder Elements:</b> Modern HTML5 <code>&lt;video id='webcam-video' autoplay playsinline&gt;&lt;/video&gt;</code> and hidden <code>&lt;canvas id='webcam-canvas'&gt;&lt;/canvas&gt;</code> elements capture live video streams for photo punch-in.<br/>"
        "• <b>Form Security & File Uploads:</b> All forms enforce CSRF tokens (<code>{% csrf_token %}</code>) and support file/document uploads using <code>enctype='multipart/form-data'</code>.",
        body_style
    ))

    sample_html = (
        "<!-- HTML5 Webcam Viewfinder & Duty Punch Terminal Component -->\n"
        "<div class=\"punch-terminal-card\">\n"
        "    <div class=\"webcam-container\">\n"
        "        <video id=\"webcam-video\" autoplay playsinline muted></video>\n"
        "        <canvas id=\"webcam-canvas\" style=\"display: none;\"></canvas>\n"
        "        <div class=\"gps-badge\" id=\"gps-display\"><i class=\"fas fa-map-marker-alt\"></i> Acquiring GPS...</div>\n"
        "    </div>\n"
        "    <div class=\"punch-controls\">\n"
        "        <button type=\"button\" class=\"btn btn-success\" id=\"btn-punch-in\"><i class=\"fas fa-sign-in-alt\"></i> Punch In</button>\n"
        "        <button type=\"button\" class=\"btn btn-danger\" id=\"btn-punch-out\"><i class=\"fas fa-sign-out-alt\"></i> Punch Out</button>\n"
        "    </div>\n"
        "</div>"
    )
    story.append(Paragraph(sample_html.replace("\n", "<br/>").replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;"), code_style))
    story.append(Spacer(1, 4))

    # CSS3 Sub-section
    story.append(Paragraph("5.2 Custom CSS3 Design System & Responsive Layouts", h2_style))
    story.append(Paragraph(
        "• <b>CSS Variables (Theming):</b> Root stylesheet defines standard corporate colors: <code>--primary-color: #1e3a8a;</code>, <code>--secondary-color: #0284c7;</code>, <code>--dark-slate: #0f172a;</code>.<br/>"
        "• <b>Flexbox & CSS Grid:</b> Dashboard layout uses CSS Grid (<code>grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));</code>) for auto-adapting KPI cards across mobile, tablet, and widescreen monitors.<br/>"
        "• <b>Attendance Calendar Badges:</b> Solid Green (Present, Holiday, Sunday), Solid Yellow (Half Day), Green with Yellow Border (Approved Permission), Solid Red (Absent / LWP), and Muted Gray (Pre-Joining Inactive).<br/>"
        "• <b>4-Record & 5-Record Scroll Containers:</b> Embedded tables use constrained max-height containers (<code>max-height: 280px; overflow-y: auto;</code>) preventing page elongation.",
        body_style
    ))

    sample_css = (
        "/* Attendance Calendar High-Contrast Color System */\n"
        ".calendar-day.present       { background-color: #059669; color: #ffffff; font-weight: bold; }\n"
        ".calendar-day.half-day      { background-color: #eab308; color: #0f172a; font-weight: bold; }\n"
        ".calendar-day.absent        { background-color: #dc2626; color: #ffffff; font-weight: bold; }\n"
        ".calendar-day.permission    { background-color: #059669; border: 2.5px solid #facc15; color: #ffffff; }\n"
        ".calendar-day.office-leave  { background-color: #7c3aed; color: #ffffff; font-weight: bold; }\n"
        ".calendar-day.pre-joining   { background-color: #f1f5f9; color: #94a3b8; cursor: not-allowed; }"
    )
    story.append(Paragraph(sample_css.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Spacer(1, 4))

    # JavaScript Sub-section
    story.append(Paragraph("5.3 Client-Side JavaScript (ES6+): WebRTC Camera & Geolocation APIs", h2_style))
    story.append(Paragraph(
        "• <b>WebRTC Camera Stream Initialization:</b> Invokes <code>navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })</code> to bind live hardware webcam video to the viewfinder.<br/>"
        "• <b>Snapshot Frame Capture:</b> Draws current video frame onto hidden HTML5 canvas: <code>canvas.getContext('2d').drawImage(video, 0, 0, 640, 480)</code>, converting image to Base64 PNG via <code>canvas.toDataURL('image/png')</code>.<br/>"
        "• <b>W3C GPS Geolocation:</b> Calls <code>navigator.geolocation.getCurrentPosition()</code> with <code>enableHighAccuracy: true, timeout: 10000</code> to capture real-time latitude and longitude coordinates.<br/>"
        "• <b>Asynchronous AJAX POST:</b> Submits captured photo data and GPS coordinates to <code>/attendance/punch-in/</code> via <code>fetch()</code> API with <code>X-CSRFToken</code> header.<br/>"
        "• <b>Password Visibility Toggle:</b> Interactive eye icon (👁️) dynamically switches input between <code>type='password'</code> and <code>type='text'</code>.",
        body_style
    ))

    sample_js = (
        "// Live Camera Snapshot and GPS Attendance Submission (ES6+)\n"
        "async function captureAndPunch(punchType) {\n"
        "    const video = document.getElementById('webcam-video');\n"
        "    const canvas = document.getElementById('webcam-canvas');\n"
        "    canvas.width = 640; canvas.height = 480;\n"
        "    canvas.getContext('2d').drawImage(video, 0, 0, 640, 480);\n"
        "    const photoDataUrl = canvas.toDataURL('image/jpeg', 0.85);\n"
        "\n"
        "    navigator.geolocation.getCurrentPosition(async (pos) => {\n"
        "        const payload = {\n"
        "            photo: photoDataUrl,\n"
        "            latitude: pos.coords.latitude,\n"
        "            longitude: pos.coords.longitude\n"
        "        };\n"
        "        const res = await fetch(`/attendance/punch-${punchType}/`, {\n"
        "            method: 'POST',\n"
        "            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },\n"
        "            body: JSON.stringify(payload)\n"
        "        });\n"
        "        const data = await res.json();\n"
        "        if (data.status === 'success') { window.location.reload(); }\n"
        "        else { alert('Attendance Error: ' + data.message); }\n"
        "    }, (err) => { alert('GPS Geolocation Error: Please enable location services.'); }, { enableHighAccuracy: true });\n"
        "}"
    )
    story.append(Paragraph(sample_js.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 6: PROJECT DIRECTORY STRUCTURE & RUN SCRIPTS
    # =========================================================================
    story.append(Paragraph("6. Project Code Structure & Execution Commands", h1_style))
    story.append(Paragraph(
        "Complete directory hierarchy and one-click execution commands for running the project on local, LAN, and production environments:",
        body_style
    ))

    tree_text = (
        "employee_management/\n"
        "├── manage.py                   # Django CLI management executable\n"
        "├── requirements.txt            # Python package dependencies\n"
        "├── run_server.bat              # One-click Windows launcher (Local & LAN)\n"
        "├── .env                        # Environment variables (SECRET_KEY, DB credentials)\n"
        "├── config/                     # Django core project configuration\n"
        "│   ├── settings.py             # Global settings, DB, static, middleware\n"
        "│   ├── urls.py                 # Root URL router\n"
        "│   └── wsgi.py                 # WSGI application entry for Gunicorn\n"
        "├── apps/                       # Modular business logic applications\n"
        "│   ├── users/                  # Custom auth, login, profiles, context processors\n"
        "│   ├── employees/              # Master staff registry, joining date, documents\n"
        "│   ├── departments/            # Departments & designations\n"
        "│   ├── attendance/             # GPS & photo punch, audit logs, daily work\n"
        "│   ├── leave_management/       # Leave requests, 2-hr permissions, monthly credit\n"
        "│   ├── payroll/                # Salary structure, attendance-based salary calculations\n"
        "│   ├── dashboard/              # Role-based dashboards (Admin, HR, Employee)\n"
        "│   └── reports/                # Excel (.xlsx) and PDF export engine\n"
        "├── templates/                  # Server-rendered HTML5 templates\n"
        "├── static/                     # CSS stylesheets, JavaScript files, corporate images\n"
        "├── media/                      # Uploaded staff documents, profile photos, punch proofs\n"
        "└── database/                   # Schema SQL scripts and JSON backup fixtures"
    )
    story.append(Paragraph(tree_text.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("One-Click Launcher Script (run_server.bat):", h2_style))
    bat_code = (
        "@echo off\n"
        "title NETCOM Employee Management Pro - Server Launcher\n"
        "cd /d \"%~dp0\"\n"
        "echo [*] Checking database migrations...\n"
        "python manage.py migrate\n"
        "echo [*] Launching application in browser...\n"
        "start http://127.0.0.1:8000/login/\n"
        "echo [*] Starting Server on http://0.0.0.0:8000/ (Local & LAN Access)\n"
        "python manage.py runserver 0.0.0.0:8000\n"
        "pause"
    )
    story.append(Paragraph(bat_code.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=1, color=c_primary, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "<b>End of Technical & Developer Reference Guide</b> • Netcom Computers Pvt Ltd • All Rights Reserved",
        ParagraphStyle('EndFooter', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=c_muted, alignment=1)
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Successfully compiled and generated guide PDF: {filename}")


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else "Netcom_Complete_Code_Architecture_and_Developer_Guide.pdf"
    build_pdf(target)
