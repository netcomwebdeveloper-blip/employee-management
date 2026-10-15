# Django Employee Management System Pro

Fresh upgraded Django project with Employee, HR, Admin, monthly calendar, advertisement popup, HR/Admin manual attendance update and punch machine CSV update.

## Features

- Front page advertisement popup
- Login page
- Employee dashboard
- HR dashboard
- Admin page
- Django admin page
- Monthly calendar
- Working days green
- Leave days red
- Previous and next month calendar
- Casual leave balance auto adds +1 every month
- Employee punch in/out auto time
- HR punch in/out auto time
- HR/Admin can update employee in/out time manually
- Total working time calculated from in time and out time
- Punch machine CSV upload update
- SQLite database

## Run Commands

### Option 1: One-Click Launcher (Windows)
Double-click `run_server.bat` in the project root directory. It runs migrations and launches the browser automatically.

### Option 2: Command Line
```bash
python manage.py migrate
python manage.py create_demo_users
python manage.py runserver
```

Open your browser at:
```text
http://127.0.0.1:8000/
```

## Documentation & PDF Guide
A complete 4-page PDF guide is included:
- **`HOW_TO_RUN_PROJECT.pdf`**: Setup instructions, architecture overview, role credentials, CSV specifications, bug fixes, and FAQs.
- To re-generate the PDF at any time, run: `python generate_pdf_guide.py`

## Demo Login

Admin: admin / admin12345
HR: hr / hr12345
Employee: emp / emp12345

## Punch Machine CSV Format

Create a CSV file like:

```csv
employee_code,date,time,type
EMP001,2026-06-18,09:30:00,in
EMP001,2026-06-18,18:15:00,out
```

Upload it in the HR page.

## Add Monthly Casual Leave Manually

```bash
python manage.py add_monthly_casual_leave
```

The dashboard also auto-checks and adds one casual leave for the current month once per user.
