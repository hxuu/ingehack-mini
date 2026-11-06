"""Bursary Refund: the Faculty bursary's refund console and public sandbox."""

from __future__ import annotations

import hashlib

from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import scaffold

FLAG = scaffold.read_flag()
STUDENT_PASSWORD = scaffold.mint()

ACCOUNTS = {
    "student": STUDENT_PASSWORD,
    # The bursar is the bot's browser, not a player account. Her password IS
    # the flag: the admin-bot handler receives the team's flag at run time
    # (ctx.job.flags), so nobody can sign in as her without already seeing the
    # /statement of a refunded account — and she never appears in the (public)
    # handler source with a secret.
    "bursar": FLAG,
}

BALANCES: dict[str, float] = {
    "student": 120.0,
    "bursar": 0.0,
}

# Students whose account has received a refund from the bursary.
REFUNDED: set[str] = set()

# The public sandbox: page id -> raw HTML.
SANDBOX: dict[str, str] = {}

app = Flask(__name__)
app.secret_key = scaffold.mint()


@app.get("/")
def home():
    return redirect(url_for("statement"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if ACCOUNTS.get(username) == password:
            session["username"] = username
            return redirect(url_for("statement"))
        error = "Those details did not match an account."
    return render_template(
        "login.html", error=error, student_password=STUDENT_PASSWORD
    )


@app.get("/statement")
def statement():
    username = session.get("username")
    if username is None:
        return redirect(url_for("login"))
    balance = BALANCES.get(username, 0.0)
    return render_template(
        "statement.html",
        username=username,
        balance=balance,
        flag=FLAG if username in REFUNDED else None,
    )


@app.post("/refund")
def refund():
    # The bursar's sign-in is all this needs: if the session belongs to the
    # bursar, the refund is approved. We do not ask where the request came from.
    if session.get("username") != "bursar":
        abort(403)
    amount = float(request.form.get("amount", "0"))
    student_id = request.form.get("studentId", "")
    if student_id in BALANCES:
        BALANCES[student_id] += amount
        REFUNDED.add(student_id)
    return redirect(url_for("statement"))


@app.route("/sandbox", methods=["GET", "POST"])
def sandbox():
    if request.method == "POST":
        html = request.form.get("html", "")
        page_id = hashlib.sha256(html.encode("utf-8")).hexdigest()[:12]
        SANDBOX[page_id] = html
        return redirect(url_for("sandbox_page", page_id=page_id))
    return render_template("sandbox.html")


@app.get("/sandbox/<page_id>")
def sandbox_page(page_id: str):
    html = SANDBOX.get(page_id)
    if html is None:
        abort(404)
    return Response(html, mimetype="text/html")


@app.get("/help")
def help_page():
    return render_template("help.html")


@app.errorhandler(404)
def not_found(error):
    return render_template("notfound.html"), 404


scaffold.register_health(app)
scaffold.register_source(app, ["app.py"], template="source.html")


if __name__ == "__main__":
    scaffold.serve(app)
