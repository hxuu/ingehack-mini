"""Course Finder: the Faculty of Sciences course search and its inbox."""

from __future__ import annotations

import json

from flask import (
    Flask,
    Response,
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
    # being at the end of the challenge — and she never appears in the
    # (public) handler source with a secret.
    "assistant": NOTE,
}

MESSAGES: dict[str, list[dict[str, str]]] = {
    "student": [],
    "assistant": [],
}

SUGGESTIONS = ["BIO 101", "BIO 204", "CHEM 118", "MATH 120", "PHYS 105"]

app = Flask(__name__)
app.secret_key = scaffold.mint()


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
    return render_template("inbox.html", username=username, messages=MESSAGES[username])


@app.post("/api/inbox")
def api_inbox():
    username = session.get("username")
    if username is None:
        return jsonify({"error": "sign in first"}), 401
    recipient = request.form.get("to", "").strip()
    body = request.form.get("body", "")
    if recipient not in MESSAGES:
        return jsonify({"error": "no such account"}), 404
    MESSAGES[recipient].append({"from": username, "body": body})
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
