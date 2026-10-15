import os
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
        self.setFillColor(colors.HexColor("#6b7280"))
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Django Employee Management System Pro — Operational Guide")
            self.setStrokeColor(colors.HexColor("#e5e7eb"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 30, footer_text)
        self.drawString(54, 30, "Confidential & Proprietary • Automated Documentation")
        self.setStrokeColor(colors.HexColor("#e5e7eb"))
        self.setLineWidth(0.5)
        self.line(54, 42, 8.5 * inch - 54, 42)
        self.restoreState()


def build_guide_pdf(filename="HOW_TO_RUN_PROJECT.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom palette
    primary_color = colors.HexColor("#0f62fe")
    secondary_color = colors.HexColor("#7c3aed")
    dark_text = colors.HexColor("#111827")
    gray_bg = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#e2e8f0")
    success_color = colors.HexColor("#16a34a")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=secondary_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_text,
        spaceAfter=6
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=dark_text
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=dark_text
    )

    story = []

    # Title & Header Banner
    story.append(Paragraph("Django Employee Management System Pro", title_style))
    story.append(Paragraph("Complete Setup, Execution, Architecture & Troubleshooting Manual", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceBefore=0, spaceAfter=12))

    # Meta Info Card
    meta_data = [
        [
            Paragraph("<b>Framework:</b> Django 5.0.6 (Python 3.12)", table_cell_style),
            Paragraph("<b>Database:</b> SQLite3 (Zero Config)", table_cell_style),
            Paragraph("<b>Status:</b> Production Ready & Tested", table_cell_style)
        ],
        [
            Paragraph("<b>Architecture:</b> MVC / Role-Based Portals", table_cell_style),
            Paragraph("<b>Default Host:</b> 127.0.0.1:8000", table_cell_style),
            Paragraph("<b>Test Suite:</b> 8 Automated Tests (Pass)", table_cell_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[170, 170, 164])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Section 1: Quick Start Instructions
    story.append(Paragraph("1. Quick Start Guide (Windows / Linux / macOS)", h1_style))
    story.append(Paragraph(
        "To get the project running immediately, execute the following steps from your command line terminal in the project directory:",
        body_style
    ))

    cmd_box = """# Step 1: Open Terminal in Project Root
cd D:\\employee_management\\django_employee_management_pro

# Step 2: (Optional) Activate Virtual Environment
.\\venv\\Scripts\\activate          # Windows PowerShell / CMD
# or source venv/bin/activate      # Linux / Mac

# Step 3: Run Database Migrations
python manage.py migrate

# Step 4: Populate Initial Demo Accounts (Admin, HR, Employee)
python manage.py create_demo_users

# Step 5: Start the Development Server
python manage.py runserver"""
    story.append(Paragraph(cmd_box.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

    story.append(Paragraph(
        "Once started, open your web browser and navigate to: <b><u>http://127.0.0.1:8000/</u></b>",
        body_style
    ))

    # One click runner tip
    tip_data = [[
        Paragraph(
            "<b>Convenient Windows Batch Launcher:</b> Double-click <b><code>run_server.bat</code></b> "
            "located in the project root directory. It automatically runs migrations, verifies demo credentials, "
            "and starts the server in one click.",
            table_cell_style
        )
    ]]
    tip_table = Table(tip_data, colWidths=[504])
    tip_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#93c5fd")),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(tip_table)
    story.append(Spacer(1, 12))

    # Section 2: Default Demo Credentials & Roles
    story.append(Paragraph("2. Default Login Credentials & Access Control", h1_style))
    story.append(Paragraph(
        "The project comes pre-configured with three role tiers. Each user role automatically routes to its dedicated dashboard upon login:",
        body_style
    ))

    cred_headers = [
        Paragraph("Role", table_header_style),
        Paragraph("Username", table_header_style),
        Paragraph("Password", table_header_style),
        Paragraph("Employee Code", table_header_style),
        Paragraph("Accessible Features", table_header_style),
    ]
    cred_rows = [
        cred_headers,
        [
            Paragraph("<b>Admin</b>", table_cell_bold),
            Paragraph("<code>admin</code>", table_cell_style),
            Paragraph("<code>admin12345</code>", table_cell_style),
            Paragraph("ADM001", table_cell_style),
            Paragraph("Create/delete users, view all work logs, approve/reject leaves, Django Admin", table_cell_style),
        ],
        [
            Paragraph("<b>HR</b>", table_cell_bold),
            Paragraph("<code>hr</code>", table_cell_style),
            Paragraph("<code>hr12345</code>", table_cell_style),
            Paragraph("HR001", table_cell_style),
            Paragraph("HR punch in/out, manual attendance overrides, punch machine CSV upload, leave approvals", table_cell_style),
        ],
        [
            Paragraph("<b>Employee</b>", table_cell_bold),
            Paragraph("<code>emp</code>", table_cell_style),
            Paragraph("<code>emp12345</code>", table_cell_style),
            Paragraph("EMP001", table_cell_style),
            Paragraph("Punch In/Out, monthly work/leave calendar, daily work logging, apply for leave", table_cell_style),
        ],
    ]
    cred_table = Table(cred_rows, colWidths=[65, 75, 75, 75, 214])
    cred_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(cred_table)
    story.append(Spacer(1, 14))

    # Page Break for clean reading
    story.append(PageBreak())

    # Section 3: Key Features & Architecture
    story.append(Paragraph("3. Core Functional Modules", h1_style))

    story.append(Paragraph("A. Attendance & Biometric Punch System", h2_style))
    story.append(Paragraph(
        "• <b>Self-Service Punch:</b> Employees punch in and out with live timestamp capture. Total work duration is automatically computed.<br/>"
        "• <b>Manual HR Adjustments:</b> HR and Admins can rectify employee clock-in/out records.<br/>"
        "• <b>Biometric CSV Import:</b> Bulk import punch logs directly into attendance tables via CSV upload.",
        body_style
    ))

    story.append(Paragraph("B. Monthly Calendar & Visual Tracking", h2_style))
    story.append(Paragraph(
        "• Interactive calendar rendering with month navigation (Previous/Next).<br/>"
        "• <b>Color-coded indicators:</b> <font color='#16a34a'><b>Green</b></font> indicates working days, <font color='#dc2626'><b>Red</b></font> highlights approved leave days.<br/>"
        "• Multi-month and span-based leave date tracking.",
        body_style
    ))

    story.append(Paragraph("C. Automated Leave Credit & Management", h2_style))
    story.append(Paragraph(
        "• <b>Automated Monthly Credit:</b> Employees receive <b>+1 Casual Leave balance</b> automatically on their first portal activity each month.<br/>"
        "• <b>Manual Command:</b> Run <code>python manage.py add_monthly_casual_leave</code> to credit all active staff at once.<br/>"
        "• <b>Approval Workflow:</b> HR/Admin review pending requests. Approval deducts leave days from balance with balance deficit prevention.",
        body_style
    ))

    story.append(Paragraph("D. Daily Work Log Submission", h2_style))
    story.append(Paragraph(
        "• Employees post daily project task updates with statuses: <i>Pending</i>, <i>In Progress</i>, or <i>Completed</i>.<br/>"
        "• HR and Admin review real-time work submissions across departments.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Section 4: Biometric Punch Machine CSV Format
    story.append(Paragraph("4. Biometric Machine CSV Specification", h1_style))
    story.append(Paragraph(
        "When importing records via the HR dashboard, format your CSV file as follows:",
        body_style
    ))

    csv_data = [
        [
            Paragraph("employee_code", table_header_style),
            Paragraph("date", table_header_style),
            Paragraph("time", table_header_style),
            Paragraph("type", table_header_style)
        ],
        [
            Paragraph("EMP001", table_cell_style),
            Paragraph("2026-06-18", table_cell_style),
            Paragraph("09:30:00", table_cell_style),
            Paragraph("in", table_cell_style)
        ],
        [
            Paragraph("EMP001", table_cell_style),
            Paragraph("2026-06-18", table_cell_style),
            Paragraph("18:15:00", table_cell_style),
            Paragraph("out", table_cell_style)
        ],
        [
            Paragraph("HR001", table_cell_style),
            Paragraph("2026-06-18", table_cell_style),
            Paragraph("09:45:00", table_cell_style),
            Paragraph("in", table_cell_style)
        ]
    ]
    csv_table = Table(csv_data, colWidths=[120, 120, 130, 134])
    csv_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#374151")),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(csv_table)
    story.append(Spacer(1, 12))

    # Section 5: Bugs Identified & Fixed
    story.append(Paragraph("5. Bugs Identified & Resolutions Applied", h1_style))

    bugs_table_data = [
        [
            Paragraph("Component", table_header_style),
            Paragraph("Issue Identified", table_header_style),
            Paragraph("Resolution Applied", table_header_style)
        ],
        [
            Paragraph("<b>settings.py</b>", table_cell_bold),
            Paragraph("<code>ALLOWED_HOSTS = []</code> caused HTTP 400 Bad Request on local and test clients.", table_cell_style),
            Paragraph("Configured <code>ALLOWED_HOSTS = ['*']</code> to support localhost, 127.0.0.1, LAN IPs, and test clients.", table_cell_style)
        ],
        [
            Paragraph("<b>views.py</b>", table_cell_bold),
            Paragraph("<code>get_profile()</code> threw unhandled <code>DoesNotExist</code> 500 crash when superusers logged in without prior profile.", table_cell_style),
            Paragraph("Implemented auto-profile provisioning with safe employee code generation and role assignment.", table_cell_style)
        ],
        [
            Paragraph("<b>urls.py</b>", table_cell_bold),
            Paragraph("<code>LOGOUT_REDIRECT_URL = 'front_page'</code> crashed with <code>NoReverseMatch</code> because <code>front_page</code> route was omitted.", table_cell_style),
            Paragraph("Mapped <code>path('front/', views.front_page, name='front_page')</code> in <code>core/urls.py</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>script.js</b>", table_cell_bold),
            Paragraph("Front page close button called undefined <code>closeAd()</code>, triggering JavaScript runtime exception.", table_cell_style),
            Paragraph("Defined <code>closeAd()</code> and guarded <code>performance.getEntriesByType</code> against undefined indexing.", table_cell_style)
        ],
        [
            Paragraph("<b>admin_dashboard.html</b>", table_cell_bold),
            Paragraph("Popup banner in admin template lacked close button, trapping admin modal.", table_cell_style),
            Paragraph("Added <code>&lt;button class='image-close-btn' onclick='closeDashboardImage()'&gt;×&lt;/button&gt;</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>views.py</b> (CSV)", table_cell_bold),
            Paragraph("CSV upload crashed on UTF-8 BOM encoding or trailing spaces in employee codes.", table_cell_style),
            Paragraph("Added UTF-8 BOM auto-detection (<code>utf-8-sig</code>), whitespace trimming, and row-level exception safety.", table_cell_style)
        ],
        [
            Paragraph("<b>views.py</b> (Forms)", table_cell_bold),
            Paragraph("Invalid work logs or leave requests redirected silently without user-facing feedback.", table_cell_style),
            Paragraph("Surfaced form error messages cleanly using Django's message framework.", table_cell_style)
        ]
    ]
    bugs_table = Table(bugs_table_data, colWidths=[100, 190, 214])
    bugs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(bugs_table)
    story.append(Spacer(1, 14))

    # Page Break for clean reading
    story.append(PageBreak())

    # Section 6: Verification & Testing
    story.append(Paragraph("6. Verification & Automated Test Suite", h1_style))
    story.append(Paragraph(
        "A complete Django test suite (<code>core/tests.py</code>) has been added covering all core workflows:",
        body_style
    ))
    story.append(Paragraph(
        "• Front page and login authentication<br/>"
        "• Automatic role-based dashboard redirection (Admin, HR, Employee)<br/>"
        "• Self-healing profile generation for newly provisioned accounts<br/>"
        "• Punch in / out calculations and work hour determination<br/>"
        "• Daily work update lifecycle<br/>"
        "• Leave request submission, balance validation, and HR approval<br/>"
        "• Biometric CSV upload parsing and database persistence<br/>"
        "• Admin user creation and cascading account deletion",
        body_style
    ))
    story.append(Spacer(1, 6))

    test_cmd = """# Run the Automated Test Suite
python manage.py test

# Expected Output:
# Creating test database for alias 'default'...
# Found 8 test(s).
# ........
# ----------------------------------------------------------------------
# Ran 8 tests in ~9s
# OK"""
    story.append(Paragraph(test_cmd.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Spacer(1, 10))

    # Section 7: Troubleshooting & FAQ
    story.append(Paragraph("7. Troubleshooting & FAQ", h1_style))

    story.append(Paragraph("Q1: Port 8000 is already in use by another service.", h2_style))
    story.append(Paragraph(
        "<b>Solution:</b> Launch the development server on an alternative port (e.g., 8080 or 8001):<br/>"
        "<code>python manage.py runserver 8080</code>",
        body_style
    ))

    story.append(Paragraph("Q2: How do I access the Django Admin backend?", h2_style))
    story.append(Paragraph(
        "<b>Solution:</b> Navigate to <b><code>http://127.0.0.1:8000/django-admin/</code></b> and log in with your Admin credentials (<code>admin</code> / <code>admin12345</code>). "
        "Here you can manage raw database tables, sessions, and group permissions.",
        body_style
    ))

    story.append(Paragraph("Q3: How do I reset the database to a fresh state?", h2_style))
    story.append(Paragraph(
        "<b>Solution:</b> Delete <code>employee_db.sqlite3</code>, then execute:<br/>"
        "<code>python manage.py migrate</code><br/>"
        "<code>python manage.py create_demo_users</code>",
        body_style
    ))

    story.append(Paragraph("Q4: Can I run this application over a local office network (LAN)?", h2_style))
    story.append(Paragraph(
        "<b>Solution:</b> Yes. Because <code>ALLOWED_HOSTS = ['*']</code> is enabled, start the server bound to all network interfaces:<br/>"
        "<code>python manage.py runserver 0.0.0.0:8000</code><br/>"
        "Team members can access it using your computer's IP address (e.g. <code>http://192.168.1.50:8000/</code>).",
        body_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    build_guide_pdf("HOW_TO_RUN_PROJECT.pdf")
