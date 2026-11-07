"""Course Finder: the Faculty of Sciences module search and its inbox."""

from __future__ import annotations

import json
import re
import secrets

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import scaffold

NOTE = scaffold.read_flag()
STUDENT_PASSWORD = scaffold.mint()

ACCOUNTS = {
    "student": STUDENT_PASSWORD,
    # The library assistant is the bot's browser, not a player account. Her
    # password IS the flag: the admin-bot handler receives the team's flag at
    # run time (ctx.job.flags), so nobody can sign in as her without already
    # being at the end of the challenge. She never appears in the
    # (public) handler source with a secret.
    "assistant": NOTE,
}

# Messages are filed under the claim code on the player's own inbox, not under
# the shared student account. The container stays static, but one team's note
# no longer appears in another team's inbox.
INBOXES: dict[str, list[dict[str, str]]] = {}

CLAIM_RE = re.compile(r"[0-9a-f]{8}")

SUGGESTIONS = ["BIO 101", "CHIM 102", "MATH 101", "PHY 105", "INFO 110"]

DISPLAY_NAMES = {
    "student": "Yacine Benali",
    "assistant": "Mme. Samira Haddad",
}

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


@app.after_request
def add_policy(response: Response) -> Response:
    """Every response, including static files and errors, carries the policy."""
    response.headers["Content-Security-Policy"] = "script-src 'self'"
    return response


@app.get("/")
def home():
    return redirect(url_for("search"))


@app.get("/search")
def search():
    query = request.args.get("q", "")
    return render_template("search.html", query=query)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if ACCOUNTS.get(username) == password:
            session["username"] = username
            return redirect(url_for("inbox"))
        error = "Those details did not match an account."
    return render_template(
        "login.html", error=error, student_password=STUDENT_PASSWORD
    )


@app.get("/inbox")
def inbox():
    username = session.get("username")
    if username is None:
        return redirect(url_for("login"))
    claim = current_claim()
    messages = [
        {
            "from": DISPLAY_NAMES.get(message["from"], message["from"]),
            "body": message["body"],
        }
        for message in INBOXES.get(claim, [])
    ]
    return render_template(
        "inbox.html",
        username=username,
        display_name=DISPLAY_NAMES.get(username, username),
        claim=claim,
        messages=messages,
    )


@app.post("/api/inbox")
def api_inbox():
    username = session.get("username")
    if username is None:
        return jsonify({"error": "sign in first"}), 401
    recipient = request.form.get("to", "").strip()
    body = request.form.get("body", "")
    if not CLAIM_RE.fullmatch(recipient):
        return jsonify({"error": "no such account"}), 404
    INBOXES.setdefault(recipient, []).append({"from": username, "body": body})
    return jsonify({"ok": True})


@app.get("/api/me/note")
def my_note():
    username = session.get("username")
    if username is None:
        return Response("sign in first\n", status=401, mimetype="text/plain")
    if username != "assistant":
        return Response("there is no note here for you\n", status=403, mimetype="text/plain")
    return Response(NOTE + "\n", mimetype="text/plain")


@app.get("/api/jsonp")
def jsonp():
    data = {"suggestions": SUGGESTIONS, "term": request.args.get("q", "")}
    # The old course widget sends the name of the function it wants called,
    # so we put that name straight into the script we send back.
    callback = request.args.get("cb", "")
    return Response(f"{callback}({json.dumps(data)})", mimetype="application/javascript")


scaffold.register_health(app)
scaffold.register_source(
    app, ["app.py", "templates/search.html"], template="source.html"
)


@app.errorhandler(404)
def not_found(error):
    return render_template("notfound.html"), 404


if __name__ == "__main__":
    scaffold.serve(app)
