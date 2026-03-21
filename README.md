# Parent Visitor Log System

A Flask-based visitor management app for tracking parent visits, validating student roll numbers, and managing live entries from an admin dashboard.

## Technologies Used
- Python
- Flask
- SQLite
- Bootstrap 5
- jQuery
- Jinja2

## Features
- Admin login for protected access to dashboard, visitor log, and sign-in flow
- Dashboard with total visitors, active visitors, daily counts, branch overview, and visit trends
- Search and filters for parent name, phone, student name, roll number, purpose, branch, status, and visit date
- CSV export for the current filtered visitor list
- Parent sign-in with 10-digit phone validation and roll number validation
- Duplicate active-visit prevention for the same parent and student
- Safer POST-based sign-out flow with visit duration tracking

## Default Admin Credentials
- Username: `admin`
- Password: `admin123`

You can override them with environment variables:

```powershell
$env:ADMIN_USERNAME="your_username"
$env:ADMIN_PASSWORD="your_password"
$env:SECRET_KEY="your_secret_key"
python app.py
```

## Setup

1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Start the app:
   ```powershell
   python app.py
   ```
3. Open `http://127.0.0.1:5000`
4. Sign in with the admin credentials above

## Main Routes
- `/login` - Admin login
- `/dashboard` - Analytics dashboard
- `/visitors` - Visitor log with filters and export
- `/signin` - Parent visitor registration form
- `/export` - CSV export for the current filter selection
