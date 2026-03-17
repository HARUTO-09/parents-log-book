from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = "visitorlog123"

ROLL_NO_PATTERN = re.compile(r"^(AIE|CSE|CCE|AID)(23|24|25)(\d{3})$")
BRANCH_NAMES = {
    "AIE": "Artificial Intelligence and Engineering",
    "CSE": "Computer Science and Engineering",
    "CCE": "Computer and Communication Engineering",
    "AID": "Artificial Intelligence and Data Science",
}

def get_db():
    conn = sqlite3.connect("visitors.db")
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

def init_db():
    conn = get_db()
    conn.execute("""
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
    """)
    columns = get_visitor_columns(conn)
    if "student_name" not in columns:
        conn.execute("ALTER TABLE visitors ADD COLUMN student_name TEXT NOT NULL DEFAULT ''")
        columns.add("student_name")
    if "roll_no" not in columns:
        conn.execute("ALTER TABLE visitors ADD COLUMN roll_no TEXT NOT NULL DEFAULT ''")
        columns.add("roll_no")
    if "whom_to_meet" in columns:
        conn.execute("""
            UPDATE visitors
            SET student_name = whom_to_meet
            WHERE (student_name IS NULL OR student_name = '')
              AND whom_to_meet IS NOT NULL
              AND whom_to_meet != ''
        """)
    conn.commit()
    conn.close()
@app.route("/")
def home():
    conn = get_db()
    visitors = conn.execute("SELECT * FROM visitors ORDER BY id DESC").fetchall()
    conn.close()
    visitor_rows = []
    for visitor in visitors:
        visitor_row = dict(visitor)
        visitor_row["roll_details"] = parse_roll_no(visitor["roll_no"])
        visitor_rows.append(visitor_row)
    return render_template("index.html", visitors=visitor_rows)
@app.route("/signin", methods=["GET", "POST"])
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
        roll_details = parse_roll_no(roll_no)
        if roll_details is None:
            flash("Enter a valid student roll number like AIE23150, CSE23001, CCE24005, or AID23140.", "danger")
            return redirect(url_for("signin"))
        conn = get_db()
        columns = get_visitor_columns(conn)
        sign_in_time = datetime.now().strftime("%Y-%m-%d %H:%M")

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
        flash("Parent visitor signed in successfully!", "success")
        return redirect(url_for("home"))
    return render_template("signin.html")
@app.route("/signout/<int:visitor_id>")
def signout(visitor_id):
    conn = get_db()
    conn.execute(
        "UPDATE visitors SET sign_out = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M"), visitor_id)
    )
    conn.commit()
    conn.close()
    flash("Parent visitor signed out successfully!", "success")
    return redirect(url_for("home"))
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
