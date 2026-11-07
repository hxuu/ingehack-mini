"""El Minha: the Faculty minha office's refund console and public sandbox."""

from __future__ import annotations

import hashlib
import re
import secrets

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
    # The minha officer is the bot's browser, not a player account. Her password IS
    # the flag: the admin-bot handler receives the team's flag at run time
    # (ctx.job.flags), so nobody can sign in as her without already seeing the
    # /statement of a refunded account. She never appears in the (public)
    # handler source with a secret.
    "bursar": FLAG,
}

BALANCES: dict[str, float] = {
    "student": 1450.0,
    "bursar": 0.0,
}

DISPLAY_NAMES = {
    "student": "Yacine Benali",
    "bursar": "Mme. Nadia Cherif",
}

# Refunds are filed under the claim code printed on the player's own statement,
# not under the shared student account. The container stays static, but one
# team's refund no longer appears on another team's page.
REFUNDS: dict[str, float] = {}

# The public sandbox: page id -> raw HTML.
SANDBOX: dict[str, str] = {}

CLAIM_RE = re.compile(r"[0-9a-f]{8}")

app = Flask(__name__)
app.secret_key = scaffold.mint()


def current_claim() -> str:
    """Return this browser's claim code, creating one on first use.

    A claim can also arrive as ?claim=, which lets a two-stage solver reuse
    the code it printed earlier. Claims are random and never enumerate.
    """
    requested = request.args.get("claim", "")
    if requested:
        if not CLAIM_RE.fullmatch(requested):
            abort(400)
        session["claim"] = requested
        return requested
    claim = session.get("claim")
    if not claim:
        claim = secrets.token_hex(4)
        session["claim"] = claim
    return claim


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
    claim = current_claim()
    credit = REFUNDS.get(claim, 0.0)
    balance = BALANCES.get(username, 0.0) + credit
    return render_template(
        "statement.html",
        username=username,
        display_name=DISPLAY_NAMES.get(username, username),
        balance=balance,
        claim=claim,
        flag=FLAG if credit else None,
    )


@app.post("/refund")
def refund():
    # The minha officer's sign-in is all this needs: if the session belongs
    # to her, the refund is approved. We do not ask where the request came from.
    if session.get("username") != "bursar":
        abort(403)
    claim = request.form.get("claim", "")
    if not CLAIM_RE.fullmatch(claim):
        abort(400)
    amount = float(request.form.get("amount", "0"))
    student_id = request.form.get("studentId", "")
    if student_id in BALANCES:
        REFUNDS[claim] = REFUNDS.get(claim, 0.0) + amount
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
