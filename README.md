# parents-log-book / Visitor Log System

A simple web app to sign in and sign out school visitors, built with Flask, Bootstrap, and jQuery.

## Technologies Used
- Python (Flask)
- HTML5 + Bootstrap 5
- jQuery (form validation)
- SQLite (database)
- Jinja2 (templating)

## Setup Instructions

1. **Clone the repo**
   ```
   git clone https://github.com/HARUTO-09/parents-log-book
   cd visitor_log
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```
   python app.py
   ```

4. Open `http://127.0.0.1:5000`

## Features
- Sign in a visitor with name, phone, purpose, and whom to meet
- View all visitors in a table
- Sign out a visitor with one click
- 10-digit phone validation using jQuery
- SQLite database (auto-created)
