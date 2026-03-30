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

## Local Development Credentials
- Username: `admin`
- Password: `admin123`

You can override them with environment variables:

```powershell
$env:ADMIN_USERNAME="your_username"
$env:ADMIN_PASSWORD="your_password"
$env:SECRET_KEY="your_secret_key"
python app.py
```

Hosted deployments now require `SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` to be set as environment variables.

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
4. Sign in with the local development credentials above

## Deployment

This project is easiest to deploy on `Railway` in its current form because it uses `SQLite`.

### Recommended: Railway + Volume

1. Push this project to GitHub.
2. In Railway, create a new project and deploy it from your GitHub repo.
3. Add a `Volume` to the service and mount it at `/data`.
4. Set these environment variables in Railway:

   ```text
   SECRET_KEY=replace-with-a-long-random-secret
   ADMIN_USERNAME=your_admin_username
   ADMIN_PASSWORD=your_admin_password
   DATABASE_PATH=/data/visitors.db
   ```

5. Deploy the service.
6. Open the generated Railway domain and sign in.

The database file and table are created automatically when the app boots.

### Railway Click Path

1. Go to `railway.app` and sign in.
2. Click `New Project`.
3. Choose `Deploy from GitHub repo`.
4. Select your `parents-log-book` repository.
5. Open the new service.
6. Go to `Variables` and add:
   `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `DATABASE_PATH`
7. Go to `Settings` -> `Volumes`.
8. Create a volume and mount it at `/data`.
9. Trigger a redeploy.
10. Visit your app URL and confirm `/health` returns a healthy response.

### Important SQLite Note

- Do not rely on the app's default `visitors.db` path in production unless your host provides persistent storage.
- Railway `Volumes` preserve the SQLite file between restarts and redeploys.
- If you push this repo to a public GitHub repository, do not publish a real `visitors.db` file with visitor data in it.

### Included Project Config

This repo now includes:

- `gunicorn` for production hosting on Linux-based platforms
- `railway.toml` with the start command and health check path
- `/health` route for deployment health checks

## Main Routes
- `/login` - Admin login
- `/dashboard` - Analytics dashboard
- `/visitors` - Visitor log with filters and export
- `/signin` - Parent visitor registration form
- `/export` - CSV export for the current filter selection
