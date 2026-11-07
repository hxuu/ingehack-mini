"""BookNook used-book store - intentionally vulnerable training challenge.

Concept: SQL injection. The search box is concatenated directly into a SQL
query, so a quote breaks the query and OR 1=1 ignores the hidden = 0 filter,
revealing a staff-only book whose title contains the flag.

See ../solution/SOLUTION.md for the intended solution and the fix.
"""

import os
import sqlite3
import threading

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

FLAG = os.environ.get("FLAG", "ingehack{undeployed}")

# Fake catalogue data. No real people or books.
VISIBLE_BOOKS = [
    ("The Clockwork Garden", "Marina Vale", 8.50),
    ("Salt & Cinder", "Ellis Ward", 6.00),
    ("A Field Guide to Small Dragons", "Tomas Reed", 12.75),
    ("Midnight at the Paper Mill", "June Calloway", 7.25),
    ("The Last Lighthouse Keeper", "Sam Ortiz", 9.00),
    ("Borrowed Weather", "Priya Nair", 5.50),
    ("Murder in the Margins", "D. K. Shaw", 10.00),
    ("The Quiet Cartographer", "Nora Flint", 11.20),
    ("Tea for the End of the World", "Ivy Marsh", 6.75),
    ("How to Read a River", "Leo Tanaka", 8.00),
    ("The Museum of Lost Sounds", "Ada Brooks", 13.40),
    ("Sixteen Kinds of Rain", "Miles Fen", 7.90),
    ("The Bookshop at the Edge of Sleep", "Rosa Haze", 9.60),
    ("Letters from the Blue Hour", "Caleb North", 5.95),
    ("The Gravity of Ordinary Things", "Lena Wren", 10.50),
]

HIDDEN_BOOK = ("Staff Preview - " + FLAG, "BookNook Staff", 0.00)

# One in-memory database per worker. It is created and seeded at startup.
_db_lock = threading.Lock()
_db = sqlite3.connect(":memory:", check_same_thread=False)
_db.row_factory = sqlite3.Row


def init_db():
    """Create the books table and load the fake catalogue."""
    with _db_lock:
        _db.execute(
            """
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                price REAL NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        _db.executemany(
            "INSERT INTO books (title, author, price, hidden) VALUES (?, ?, ?, 0)",
            VISIBLE_BOOKS,
        )
        _db.execute(
            "INSERT INTO books (title, author, price, hidden) VALUES (?, ?, ?, 1)",
            HIDDEN_BOOK,
        )
        _db.commit()


init_db()


@app.get("/")
def index():
    return redirect(url_for("search"))


@app.get("/search")
def search():
    q = request.args.get("q", "")

    # VULN: user input is concatenated straight into the SQL query, so the
    # attacker can rewrite the WHERE clause (and break the syntax with a quote).
    sql = (
        "SELECT id, title, author, price FROM books "
        "WHERE hidden = 0 AND title LIKE '%" + q + "%'"
    )

    rows = None
    error = None
    try:
        with _db_lock:
            rows = [dict(row) for row in _db.execute(sql).fetchall()]
    except sqlite3.Error as exc:
        # Debug-style error message, deliberately shown to the player. The
        # driver message is short and contains no filesystem paths.
        error = str(exc)

    return render_template("index.html", q=q, rows=rows, error=error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
