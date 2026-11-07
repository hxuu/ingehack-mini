"""FlashMart - intentionally vulnerable race-condition training challenge.

Concept: time-of-check to time-of-use (TOCTOU). `/redeem` checks whether the
single-use coupon FLASH50 was already used, then does some slow "backend work",
and only afterwards updates the balance and the coupon flag. Parallel requests
can all pass the check before any of them writes the result, so one coupon can
be redeemed several times.

`/buy` is deliberately written correctly (a single atomic UPDATE), so the ONLY
vulnerability in this app is the check-then-use sequence in `/redeem`.

See solution/SOLUTION.md for the intended solution and the fix.
"""

import os
import secrets
import sqlite3
import time

from flask import Flask, redirect, render_template, request, session, url_for

# The platform injects the real flag through FLAG; never hardcode it in src/.
FLAG = os.environ.get("FLAG", "ingehack{undeployed}")

# The root filesystem is read-only, so the database lives on the writable
# /tmp tmpfs provided by the deployment.
DB_PATH = os.environ.get("DB_PATH", "/tmp/flashmart.db")

COUPON_CODE = "FLASH50"
COUPON_VALUE = 50
STARTING_BALANCE = 10
FLAG_PACK_PRICE = 200

app = Flask(__name__)

app.config.update(
    # Stable signed-session key. deploy-static.sh injects only FLAG, so derive
    # the key from the secret flag: every gunicorn thread/worker then agrees on
    # the same unguessable key without a separate SECRET_KEY env var.
    SECRET_KEY=os.environ.get("SECRET_KEY") or FLAG + ":flashmart-session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # the training container runs over plain HTTP
)


def open_db():
    """Open a fresh SQLite connection for this request/thread.

    One connection per request keeps gunicorn's worker threads from sharing a
    connection object. Autocommit mode means every statement is committed
    immediately, and the busy timeout makes concurrent writers wait instead of
    failing with "database is locked".
    """
    conn = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db():
    """Create the users table once, before gunicorn starts serving requests."""
    conn = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL UNIQUE,
            balance INTEGER NOT NULL DEFAULT 10,
            flash50_redeemed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.close()


init_db()


def load_or_create_user(conn):
    """Return the shopper tied to this signed session, creating one on first visit."""
    user_id = session.get("user_id")
    if user_id is not None:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is not None:
            return row

    token = secrets.token_hex(16)
    cursor = conn.execute(
        "INSERT INTO users (token, balance) VALUES (?, ?)",
        (token, STARTING_BALANCE),
    )
    session["user_id"] = cursor.lastrowid
    return conn.execute(
        "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()


def shop_page(user, message=None, error=None, flag=None):
    return render_template(
        "index.html",
        user=user,
        message=message,
        error=error,
        flag=flag,
        coupon_code=COUPON_CODE,
        coupon_value=COUPON_VALUE,
        flag_pack_price=FLAG_PACK_PRICE,
    )


@app.get("/")
def index():
    conn = open_db()
    try:
        user = load_or_create_user(conn)
        return shop_page(user)
    finally:
        conn.close()


@app.post("/redeem")
def redeem():
    conn = open_db()
    try:
        user = load_or_create_user(conn)
        code = request.form.get("code", "").strip().upper()

        if code != COUPON_CODE:
            return shop_page(
                user,
                error="That coupon code is not valid. The active promo code is "
                + COUPON_CODE
                + ".",
            )

        # VULN: TOCTOU. This CHECK and the USE further down are two separate
        # steps with no lock, transaction, or conditional UPDATE around them.
        # Parallel requests all read "not redeemed yet" and then all add credits.
        already_redeemed = conn.execute(
            "SELECT flash50_redeemed FROM users WHERE id = ?", (user["id"],)
        ).fetchone()["flash50_redeemed"]

        if already_redeemed:
            return shop_page(
                user,
                error="You have already used the " + COUPON_CODE + " coupon.",
            )

        # Simulated backend work: fraud check, audit logging, partner API call.
        # It also makes the race window wide enough to hit reliably by hand.
        time.sleep(0.05)

        # USE: last request wins, but every request that passed the check above
        # still runs this update and receives the credits.
        conn.execute(
            "UPDATE users SET balance = balance + ?, flash50_redeemed = 1 "
            "WHERE id = ?",
            (COUPON_VALUE, user["id"]),
        )

        refreshed = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
        return shop_page(
            refreshed,
            message="Coupon accepted! "
            + str(COUPON_VALUE)
            + " credits added to your balance.",
        )
    finally:
        conn.close()


@app.post("/buy")
def buy():
    conn = open_db()
    try:
        user = load_or_create_user(conn)
        item = request.form.get("item", "").strip().lower()

        if item != "flag":
            return shop_page(user, error="That item does not exist.")

        # Correct on purpose: ONE atomic statement both checks the balance and
        # deducts the price. Only the request whose UPDATE matches a row can buy.
        cursor = conn.execute(
            "UPDATE users SET balance = balance - ? "
            "WHERE id = ? AND balance >= ?",
            (FLAG_PACK_PRICE, user["id"], FLAG_PACK_PRICE),
        )

        if cursor.rowcount == 0:
            return shop_page(
                user,
                error="Not enough credits. The Flag Pack costs "
                + str(FLAG_PACK_PRICE)
                + " credits.",
            )

        refreshed = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
        return shop_page(
            refreshed,
            flag=FLAG,
            message="Purchase complete! Here is your Flag Pack.",
        )
    finally:
        conn.close()


@app.post("/new-account")
def new_account():
    """Start over with a fresh shopper (handy after a failed attempt)."""
    session.clear()
    return redirect(url_for("index"))


@app.get("/healthz")
def healthz():
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
