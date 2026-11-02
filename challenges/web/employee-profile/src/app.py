"""StaffHub employee intranet - intentionally vulnerable training challenge.

Concept: IDOR (insecure direct object reference), also called missing
object-level authorization. Every logged-in employee may read any profile by
changing the numeric `id` in /profile?id=... . The server checks *whether*
someone is logged in, but never checks *which* record they are allowed to read.

See ../solution/SOLUTION.md for the intended solution and the fix.
"""

import os
import sqlite3
import threading

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

FLAG = os.environ.get("FLAG", "ingehack{undeployed}")

app.config.update(
    # Stable so every gunicorn worker (and a restart) can verify the same
    # signed session cookie. deploy-static.sh injects only FLAG, so derive the
    # key from the secret flag when SECRET_KEY is absent: sessions keep working
    # across workers without a committed secret anyone could forge with.
    SECRET_KEY=os.environ.get("SECRET_KEY") or (FLAG + ":staffhub-session"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # the training container runs over plain HTTP
)

# Fake employees. No real people, addresses or phone numbers.
# id=1 is the CEO. id=105 is the low-privilege demo account shown on /login.
EMPLOYEES = [
    (
        1,
        "admin",
        "R3dwood-CEO!2026",
        "Maya Chen",
        "CEO",
        "Executive Office",
        "maya.chen@staffhub.example",
        "+1 555 0100",
        f"CEO private notes. Board security drill flag: {FLAG}",
    ),
    (
        101,
        "alice.wong",
        "Sunrise-101",
        "Alice Wong",
        "Software Engineer",
        "Engineering",
        "alice.wong@staffhub.example",
        "+1 555 0101",
        "Desk 3F-12. Builds the payments service. On call every third Thursday.",
    ),
    (
        102,
        "ben.okafor",
        "Sunrise-102",
        "Ben Okafor",
        "Account Executive",
        "Sales",
        "ben.okafor@staffhub.example",
        "+1 555 0102",
        "Desk 2A-04. Covers the west region. Loves a good coffee run.",
    ),
    (
        103,
        "carla.mendes",
        "Sunrise-103",
        "Carla Mendes",
        "Marketing Manager",
        "Marketing",
        "carla.mendes@staffhub.example",
        "+1 555 0103",
        "Desk 2B-07. Runs the quarterly newsletter and the launch calendar.",
    ),
    (
        104,
        "dmitri.volkov",
        "Sunrise-104",
        "Dmitri Volkov",
        "IT Support Specialist",
        "IT",
        "dmitri.volkov@staffhub.example",
        "+1 555 0104",
        "Desk 1C-02. Manages laptops, monitors and access badges.",
    ),
    (
        105,
        "guest",
        "guest123",
        "Guest User",
        "Employee",
        "Support",
        "guest@staffhub.example",
        "+1 555 0105",
        "Demo account for new starters. Everything here is fake.",
    ),
    (
        106,
        "emma.liang",
        "Sunrise-106",
        "Emma Liang",
        "Financial Analyst",
        "Finance",
        "emma.liang@staffhub.example",
        "+1 555 0106",
        "Desk 4A-03. Prepares the monthly close. Keeps the coffee fund.",
    ),
    (
        107,
        "farid.hassan",
        "Sunrise-107",
        "Farid Hassan",
        "Operations Coordinator",
        "Operations",
        "farid.hassan@staffhub.example",
        "+1 555 0107",
        "Desk 1A-08. Books meeting rooms, desks and travel.",
    ),
    (
        108,
        "grace.kim",
        "Sunrise-108",
        "Grace Kim",
        "People Ops Manager",
        "People Operations",
        "grace.kim@staffhub.example",
        "+1 555 0108",
        "Desk 2C-01. Handles onboarding, benefits and the social calendar.",
    ),
    (
        109,
        "hugo.silva",
        "Sunrise-109",
        "Hugo Silva",
        "Legal Counsel",
        "Legal",
        "hugo.silva@staffhub.example",
        "+1 555 0109",
        "Desk 4C-06. Reviews vendor contracts and answers policy questions.",
    ),
    (
        110,
        "irene.novak",
        "Sunrise-110",
        "Irene Novak",
        "Product Designer",
        "Design",
        "irene.novak@staffhub.example",
        "+1 555 0110",
        "Desk 3B-11. Owns the design system and the user research library.",
    ),
]

# One in-memory database per gunicorn worker, created and seeded at startup.
# Every worker gets the same data, and only the signed session crosses workers.
_db_lock = threading.Lock()
_db = sqlite3.connect(":memory:", check_same_thread=False)
_db.row_factory = sqlite3.Row


def init_db():
    """Create the users table and load the fake employee directory."""
    with _db_lock:
        _db.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                notes TEXT NOT NULL
            )
            """
        )
        for emp in EMPLOYEES:
            emp_id, username, password, full_name, role, department, email, phone, notes = emp
            _db.execute(
                """
                INSERT INTO users (
                    id, username, password_hash, full_name, role, department,
                    email, phone, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    emp_id,
                    username,
                    # Passwords are stored as salted hashes, never in clear text.
                    generate_password_hash(password, method="pbkdf2:sha256"),
                    full_name,
                    role,
                    department,
                    email,
                    phone,
                    notes,
                ),
            )
        _db.commit()


init_db()


def get_user_by_id(user_id):
    """Look up one employee. The value is bound as a parameter, so no SQLi."""
    with _db_lock:
        return _db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.get("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("profile", id=session["user_id"]))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with _db_lock:
            row = _db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

        if row is None or not check_password_hash(row["password_hash"], password):
            return render_template(
                "login.html", error="Invalid username or password."
            ), 401

        session.clear()
        session["user_id"] = row["id"]
        session["username"] = row["username"]
        return redirect(url_for("profile", id=row["id"]))

    if session.get("user_id"):
        return redirect(url_for("profile", id=session["user_id"]))
    return render_template("login.html", error=None)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    requested_id = request.args.get("id", type=int)
    if requested_id is None:
        return redirect(url_for("profile", id=session["user_id"]))

    # VULN: only authentication is checked here. The code never verifies that
    # requested_id belongs to session["user_id"], so any logged-in employee can
    # read any other employee's profile by changing the number in the URL.
    employee = get_user_by_id(requested_id)
    if employee is None:
        abort(404)

    viewer = get_user_by_id(session["user_id"])
    return render_template("profile.html", employee=employee, viewer=viewer)


@app.get("/healthz")
def healthz():
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
