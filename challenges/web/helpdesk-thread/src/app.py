"""Open Ticket: PackSwift's support desk and its two views of one thread."""

from __future__ import annotations

import re
import secrets

from flask import (
    Flask,
    abort,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from markupsafe import Markup

import scaffold

STUDENT_PASSWORD = scaffold.mint()
AGENT_TOKEN = scaffold.mint()
FLAG = scaffold.read_flag()

ACCOUNTS = {
    "student": {"password": STUDENT_PASSWORD, "role": "customer"},
    # The support agent is the bot's browser, not a player account. Her
    # password IS the flag: the admin-bot handler receives the team's flag at
    # run time (ctx.job.flags), so nobody can sign in as her directly. She
    # never appears in the (public) handler source with a secret.
    "agent": {"password": scaffold.read_flag(), "role": "agent"},
}

THREADS = {
    1: {
        "subject": "Parcel PS-10482 never arrived",
        "owner": "student",
        "opened": "14 Oct 2025",
        "reference": "PS-10482",
        "status": "Open",
        "messages": [
            {
                "author": "student",
                "role": "customer",
                "copy_label": "Customer copy",
                "when": "14 Oct 09:41",
                "body": "My parcel PS-10482 was marked delivered on Monday, but nobody knocked. I was home all day.",
            },
            {
                "author": "agent",
                "role": "agent",
                "copy_label": "Desk copy",
                "when": "14 Oct 11:08",
                "body": "Thanks for reporting this. I have asked the Bab Ezzouar depot to trace it.",
            },
        ],
    }
}

ROLE_BY_AUTHOR = {"student": "customer", "agent": "agent"}
COPY_BY_AUTHOR = {"student": "Customer copy", "agent": "Desk copy"}

DISPLAY_NAMES = {
    "student": "Yacine Benali",
    "agent": "Mme. Samira Haddad",
}

# The desk files each appended reply under the claim code on the customer's
# own ticket, not under the shared student account. The container stays
# static, but one team's reply no longer appears on another team's ticket.
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


def agent_page(template: str, **context):
    """Render a desk screen with the ticket token available to its scripts."""
    response = make_response(render_template(template, **context))
    # The reply form on this screen reads the ticket token out of the cookie,
    # so the cookie is stored where the page's own scripts can reach it.
    response.set_cookie("agent_token", AGENT_TOKEN, httponly=False, samesite="Lax")
    return response


def customer_messages(thread: dict, claim: str) -> list[dict[str, object]]:
    """The customer view shows the seed messages and this claim's replies."""
    return [
        {
            "author": DISPLAY_NAMES.get(message["author"], message["author"]),
            "role": message["role"],
            "copy_label": message["copy_label"],
            "when": message["when"],
            "body": message["body"],
        }
        for message in thread["messages"]
        if message.get("claim") in (None, claim)
    ]


def desk_messages(thread: dict) -> list[dict[str, object]]:
    """The desk view keeps the formatting agents and customers write."""
    # Agents paste formatted replies into the thread, so the desk view puts
    # each stored message into the page exactly as it was written.
    return [
        {
            "author": DISPLAY_NAMES.get(message["author"], message["author"]),
            "role": message["role"],
            "copy_label": message["copy_label"],
            "when": message["when"],
            "body": Markup(message["body"]),
        }
        for message in thread["messages"]
    ]


@app.errorhandler(403)
def forbidden(_error):
    return render_template("forbidden.html"), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("notfound.html"), 404


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        account = ACCOUNTS.get(username)
        if account is not None and account["password"] == password:
            session["username"] = username
            session["role"] = account["role"]
            return redirect(url_for("home"))
        error = "Those details did not match an account."
    return render_template(
        "login.html", error=error, student_password=STUDENT_PASSWORD
    )


@app.get("/")
def home():
    if session.get("username") is None:
        return redirect(url_for("login"))
    if session.get("role") == "agent":
        return redirect(url_for("agent_ticket", ticket_id=1))
    return redirect(url_for("ticket", ticket_id=1))


@app.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
def ticket(ticket_id):
    username = session.get("username")
    if username is None:
        return redirect(url_for("login"))
    thread = THREADS.get(ticket_id)
    if thread is None:
        abort(404)
    if thread["owner"] != username:
        abort(403)
    claim = current_claim()
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            thread["messages"].append(
                {
                    "author": username,
                    "role": ROLE_BY_AUTHOR[username],
                    "copy_label": COPY_BY_AUTHOR[username],
                    "when": "14 Oct 12:02",
                    "body": body,
                    "claim": claim,
                }
            )
    return render_template(
        "ticket.html",
        ticket_id=ticket_id,
        thread=thread,
        owner_display=DISPLAY_NAMES.get(thread["owner"], thread["owner"]),
        claim=claim,
        messages=customer_messages(thread, claim),
    )


@app.get("/agent/tickets/<int:ticket_id>")
def agent_ticket(ticket_id):
    if session.get("role") != "agent":
        abort(403)
    thread = THREADS.get(ticket_id)
    if thread is None:
        abort(404)
    return agent_page(
        "agent_ticket.html",
        ticket_id=ticket_id,
        thread=thread,
        owner_display=DISPLAY_NAMES.get(thread["owner"], thread["owner"]),
        messages=desk_messages(thread),
        flag=FLAG,
    )


@app.get("/agent/guidelines")
def agent_guidelines():
    return render_template("guidelines.html")


@app.post("/api/tickets/<int:ticket_id>/append")
def append_message(ticket_id):
    if session.get("role") != "agent":
        return jsonify({"error": "the desk side only"}), 403
    if request.headers.get("X-Agent-Token") != AGENT_TOKEN:
        return jsonify({"error": "the ticket token is missing"}), 403
    thread = THREADS.get(ticket_id)
    if thread is None:
        return jsonify({"error": "no such ticket"}), 404
    body = request.form.get("body", "").strip()
    if not body:
        return jsonify({"error": "nothing to add"}), 400
    claim = request.form.get("claim", "").strip()
    if claim and not CLAIM_RE.fullmatch(claim):
        return jsonify({"error": "bad claim code"}), 400
    thread["messages"].append(
        {
            "author": "agent",
            "role": "agent",
            "copy_label": "Desk copy",
            "when": "14 Oct 12:02",
            "body": body,
            "claim": claim or None,
        }
    )
    return jsonify({"ok": True})


scaffold.register_health(app)
scaffold.register_source(app, ["app.py"], template="source.html")


if __name__ == "__main__":
    scaffold.serve(app)
