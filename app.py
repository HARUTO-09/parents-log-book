import csv
import io
import os
import re
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

from flask import (
    Flask,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "visitorlog123")
app.config["ADMIN_USERNAME"] = os.environ.get("ADMIN_USERNAME", "admin")
app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "admin123")
app.config["DATABASE_PATH"] = os.environ.get("DATABASE_PATH", "visitors.db")

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"
PHONE_PATTERN = re.compile(r"^\d{10}$")
ROLL_NO_PATTERN = re.compile(r"^(AIE|CSE|CCE|AID)(23|24|25)(\d{3})$")
PURPOSE_OPTIONS = [
    "Parent Meeting",
    "Fee Enquiry",
    "Academic Discussion",
    "Leave Request",
    "Other",
]
BRANCH_NAMES = {
    "AIE": "Artificial Intelligence and Engineering",
    "CSE": "Computer Science and Engineering",
    "CCE": "Computer and Communication Engineering",
    "AID": "Artificial Intelligence and Data Science",
}
SECTION_NAMES = {
    "0": "A",
    "1": "B",
    "2": "C",
}


def get_db():
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    return conn


def get_visitor_columns(conn):
    return {row["name"] for row in conn.execute("PRAGMA table_info(visitors)").fetchall()}


def parse_roll_no(roll_no):
    match = ROLL_NO_PATTERN.fullmatch((roll_no or "").strip().upper())
    if not match:
        return None

    branch_code, admission_year_suffix, section_digits = match.groups()
    section = SECTION_NAMES.get(section_digits[0])
    if section is None or section_digits == "000":
        return None

    return {
        "normalized": f"{branch_code}{admission_year_suffix}{section_digits}",
        "branch_code": branch_code,
        "branch_name": BRANCH_NAMES[branch_code],
        "admission_year": f"20{admission_year_suffix}",
        "section": section,
    }


def parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        return None


def format_minutes(minutes):
    if minutes is None:
        return "-"

    total_minutes = max(int(minutes), 0)
    hours, remaining_minutes = divmod(total_minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if remaining_minutes or not parts:
        parts.append(f"{remaining_minutes}m")
    return " ".join(parts)


def format_visit_duration(sign_in, sign_out):
    start = parse_timestamp(sign_in)
    end = parse_timestamp(sign_out)
    if not start or not end or end < start:
        return "-"
    total_minutes = int((end - start).total_seconds() // 60)
    return format_minutes(total_minutes)


def enrich_visitor_row(row):
    visitor = dict(row)
    visitor["roll_details"] = parse_roll_no(visitor["roll_no"])
    visitor["visit_status"] = "Inside" if not visitor["sign_out"] else "Completed"
    visitor["visit_duration"] = (
        "In Progress" if not visitor["sign_out"] else format_visit_duration(visitor["sign_in"], visitor["sign_out"])
    )
    return visitor


def build_filter_values(args):
    filters = {
        "search": (args.get("search") or "").strip(),
        "purpose": (args.get("purpose") or "").strip(),
        "branch": (args.get("branch") or "").strip().upper(),
        "status": (args.get("status") or "").strip().lower(),
        "visit_date": (args.get("visit_date") or "").strip(),
    }

    if filters["purpose"] and filters["purpose"] not in PURPOSE_OPTIONS:
        filters["purpose"] = ""
    if filters["branch"] and filters["branch"] not in BRANCH_NAMES:
        filters["branch"] = ""
    if filters["status"] not in {"", "active", "completed"}:
        filters["status"] = ""
    if filters["visit_date"]:
        try:
            datetime.strptime(filters["visit_date"], "%Y-%m-%d")
        except ValueError:
            filters["visit_date"] = ""

    return filters


def build_active_filter_params(filters):
    return {key: value for key, value in filters.items() if value}


def fetch_visitors(filters=None, limit=None):
    init_db()
    filters = filters or {}
    query = ["SELECT * FROM visitors"]
    clauses = []
    params = []

    search = filters.get("search")
    if search:
        clauses.append(
            """
            (
                LOWER(name) LIKE ?
                OR phone LIKE ?
                OR LOWER(student_name) LIKE ?
                OR UPPER(roll_no) LIKE ?
            )
            """
        )
        params.extend(
            [
                f"%{search.lower()}%",
                f"%{search}%",
                f"%{search.lower()}%",
                f"%{search.upper()}%",
            ]
        )

    purpose = filters.get("purpose")
    if purpose:
        clauses.append("purpose = ?")
        params.append(purpose)

    branch = filters.get("branch")
    if branch:
        clauses.append("substr(roll_no, 1, 3) = ?")
        params.append(branch)

    status = filters.get("status")
    if status == "active":
        clauses.append("(sign_out IS NULL OR sign_out = '')")
    elif status == "completed":
        clauses.append("(sign_out IS NOT NULL AND sign_out != '')")

    visit_date = filters.get("visit_date")
    if visit_date:
        clauses.append("substr(sign_in, 1, 10) = ?")
        params.append(visit_date)

    if clauses:
        query.append("WHERE " + " AND ".join(clauses))

    query.append("ORDER BY id DESC")

    if limit is not None:
        query.append("LIMIT ?")
        params.append(limit)

    conn = get_db()
    rows = conn.execute(" ".join(query), params).fetchall()
    conn.close()
    return [enrich_visitor_row(row) for row in rows]


def calculate_dashboard_metrics():
    visitors = fetch_visitors()
    today_key = date.today().isoformat()
    branch_totals = Counter()
    branch_active_totals = Counter()
    purpose_totals = Counter()
    daily_counts = Counter()
    completed_durations = []

    for visitor in visitors:
        purpose_totals[visitor["purpose"]] += 1
        daily_counts[visitor["sign_in"][:10]] += 1

        roll_details = visitor["roll_details"]
        if roll_details:
            branch_totals[roll_details["branch_code"]] += 1
            if not visitor["sign_out"]:
                branch_active_totals[roll_details["branch_code"]] += 1

        start = parse_timestamp(visitor["sign_in"])
        end = parse_timestamp(visitor["sign_out"])
        if start and end and end >= start:
            completed_durations.append(int((end - start).total_seconds() // 60))

    trend_items = []
    max_count = 0
    for offset in range(6, -1, -1):
        current_day = date.today() - timedelta(days=offset)
        count = daily_counts[current_day.isoformat()]
        max_count = max(max_count, count)
        trend_items.append(
            {
                "date_label": current_day.strftime("%d %b"),
                "count": count,
            }
        )

    for item in trend_items:
        if max_count == 0:
            item["width"] = 0
        else:
            item["width"] = max(12, int((item["count"] / max_count) * 100)) if item["count"] else 0

    average_duration = None
    if completed_durations:
        average_duration = sum(completed_durations) // len(completed_durations)

    return {
        "total_visitors": len(visitors),
        "active_visitors": sum(1 for visitor in visitors if not visitor["sign_out"]),
        "todays_visitors": sum(1 for visitor in visitors if visitor["sign_in"].startswith(today_key)),
        "completed_today": sum(
            1 for visitor in visitors if visitor["sign_out"] and visitor["sign_out"].startswith(today_key)
        ),
        "average_visit_duration": format_minutes(average_duration),
        "branch_summary": [
            {
                "code": branch_code,
                "name": branch_name,
                "count": branch_totals[branch_code],
                "active_count": branch_active_totals[branch_code],
            }
            for branch_code, branch_name in BRANCH_NAMES.items()
        ],
        "purpose_summary": purpose_totals.most_common(),
        "visit_trend": trend_items,
        "recent_visitors": visitors[:5],
    }


def is_safe_next_url(target):
    if not target:
        return False
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == "" and target.startswith("/")


def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please sign in as an admin to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped_view


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            purpose TEXT NOT NULL,
            student_name TEXT NOT NULL DEFAULT '',
            roll_no TEXT NOT NULL DEFAULT '',
            sign_in TEXT NOT NULL,
            sign_out TEXT
        )
        """
    )

    columns = get_visitor_columns(conn)
    if "student_name" not in columns:
        conn.execute("ALTER TABLE visitors ADD COLUMN student_name TEXT NOT NULL DEFAULT ''")
        columns.add("student_name")
    if "roll_no" not in columns:
        conn.execute("ALTER TABLE visitors ADD COLUMN roll_no TEXT NOT NULL DEFAULT ''")
        columns.add("roll_no")
    if "whom_to_meet" in columns:
        conn.execute(
            """
            UPDATE visitors
            SET student_name = whom_to_meet
            WHERE (student_name IS NULL OR student_name = '')
              AND whom_to_meet IS NOT NULL
              AND whom_to_meet != ''
            """
        )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_visitors_sign_in ON visitors(sign_in)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_visitors_roll_no ON visitors(roll_no)")
    conn.commit()
    conn.close()


@app.context_processor
def inject_template_data():
    return {
        "branch_names": BRANCH_NAMES,
        "purpose_options": PURPOSE_OPTIONS,
    }


@app.route("/")
def home():
    if session.get("is_admin"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("is_admin"):
        return redirect(url_for("dashboard"))

    next_url = request.args.get("next") or request.form.get("next") or ""

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if (
            username == app.config["ADMIN_USERNAME"]
            and password == app.config["ADMIN_PASSWORD"]
        ):
            session.clear()
            session["is_admin"] = True
            session["admin_username"] = username
            flash("Admin login successful.", "success")
            if is_safe_next_url(next_url):
                return redirect(next_url)
            return redirect(url_for("dashboard"))

        flash("Invalid admin username or password.", "danger")

    return render_template("login.html", next_url=next_url)


@app.route("/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@admin_required
def dashboard():
    metrics = calculate_dashboard_metrics()
    return render_template("dashboard.html", **metrics)


@app.route("/visitors")
@admin_required
def visitor_log():
    filters = build_filter_values(request.args)
    visitors = fetch_visitors(filters)
    current_path = request.full_path if request.query_string else request.path
    current_path = current_path[:-1] if current_path.endswith("?") else current_path
    return render_template(
        "index.html",
        visitors=visitors,
        filters=filters,
        active_filter_count=sum(1 for value in filters.values() if value),
        export_url=url_for("export_visitors", **build_active_filter_params(filters)),
        current_path=current_path,
    )


@app.route("/export")
@admin_required
def export_visitors():
    filters = build_filter_values(request.args)
    visitors = fetch_visitors(filters)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Parent Name",
            "Phone",
            "Purpose",
            "Student Name",
            "Roll No",
            "Branch",
            "Admission Year",
            "Section",
            "Sign In",
            "Sign Out",
            "Status",
            "Duration",
        ]
    )

    for visitor in visitors:
        roll_details = visitor["roll_details"] or {}
        writer.writerow(
            [
                visitor["id"],
                visitor["name"],
                visitor["phone"],
                visitor["purpose"],
                visitor["student_name"],
                visitor["roll_no"],
                roll_details.get("branch_name", "-"),
                roll_details.get("admission_year", "-"),
                roll_details.get("section", "-"),
                visitor["sign_in"],
                visitor["sign_out"] or "-",
                visitor["visit_status"],
                visitor["visit_duration"],
            ]
        )

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=visitor-log-{date.today().isoformat()}.csv"
    )
    return response


@app.route("/signin", methods=["GET", "POST"])
@admin_required
def signin():
    if request.method == "POST":
        init_db()
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        purpose = (request.form.get("purpose") or "").strip()
        student_name = (request.form.get("student_name") or "").strip()
        roll_no = (request.form.get("roll_no") or "").strip().upper()

        if not all([name, phone, purpose, student_name, roll_no]):
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("signin"))
        if not PHONE_PATTERN.fullmatch(phone):
            flash("Enter a valid 10-digit phone number.", "danger")
            return redirect(url_for("signin"))

        roll_details = parse_roll_no(roll_no)
        if roll_details is None:
            flash(
                "Enter a valid student roll number like AIE23150, CSE23001, CCE24005, or AID23140.",
                "danger",
            )
            return redirect(url_for("signin"))

        conn = get_db()
        columns = get_visitor_columns(conn)
        active_duplicate = conn.execute(
            """
            SELECT id
            FROM visitors
            WHERE phone = ?
              AND roll_no = ?
              AND (sign_out IS NULL OR sign_out = '')
            LIMIT 1
            """,
            (phone, roll_details["normalized"]),
        ).fetchone()
        if active_duplicate:
            conn.close()
            flash("This parent already has an active visit entry.", "warning")
            return redirect(url_for("visitor_log"))

        sign_in_time = datetime.now().strftime(TIMESTAMP_FORMAT)

        if "whom_to_meet" in columns:
            conn.execute(
                """
                INSERT INTO visitors (
                    name, phone, purpose, whom_to_meet, student_name, roll_no, sign_in
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, phone, purpose, student_name, student_name, roll_details["normalized"], sign_in_time),
            )
        else:
            conn.execute(
                """
                INSERT INTO visitors (name, phone, purpose, student_name, roll_no, sign_in)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, phone, purpose, student_name, roll_details["normalized"], sign_in_time),
            )

        conn.commit()
        conn.close()
        flash("Parent visitor signed in successfully.", "success")
        return redirect(url_for("visitor_log"))

    return render_template("signin.html")


@app.route("/signout/<int:visitor_id>", methods=["POST"])
@admin_required
def signout(visitor_id):
    init_db()
    redirect_to = request.form.get("redirect_to") or url_for("visitor_log")
    conn = get_db()
    visitor = conn.execute("SELECT sign_out FROM visitors WHERE id = ?", (visitor_id,)).fetchone()

    if visitor is None:
        conn.close()
        flash("Visitor record not found.", "warning")
    elif visitor["sign_out"]:
        conn.close()
        flash("This visitor has already been signed out.", "info")
    else:
        conn.execute(
            "UPDATE visitors SET sign_out = ? WHERE id = ?",
            (datetime.now().strftime(TIMESTAMP_FORMAT), visitor_id),
        )
        conn.commit()
        conn.close()
        flash("Parent visitor signed out successfully.", "success")

    if is_safe_next_url(redirect_to):
        return redirect(redirect_to)
    return redirect(url_for("visitor_log"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
