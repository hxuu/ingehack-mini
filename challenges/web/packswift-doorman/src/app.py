from __future__ import annotations

import scaffold
from flask import Flask, render_template, request

app = Flask(__name__)
FLAG = scaffold.read_flag()

scaffold.register_health(app)
scaffold.register_source(app, ["app.py"], template="source.html")

ROLE_HEADER = "X-PackSwift-Role"
DEFAULT_ROLE = "customer"
DISPATCHER = "dispatcher"


def current_role():
    return request.headers.get(ROLE_HEADER, DEFAULT_ROLE)


@app.get("/")
def home():
    tracked = request.args.get("tracking", "").strip()
    return render_template("public.html", tracking=tracked)


@app.get("/portal")
def portal():
    if current_role() != DISPATCHER:
        return render_template("portal.html", allowed=False), 403
    return render_template("portal.html", allowed=True)


@app.get("/portal/dispatch")
def dispatch():
    if current_role() != DISPATCHER:
        return render_template("portal.html", allowed=False), 403
    return render_template("dispatch.html", flag=FLAG)


@app.get("/status")
def status():
    return render_template("status.html", header=ROLE_HEADER)


@app.errorhandler(404)
def not_found(error):
    return render_template("notfound.html"), 404


if __name__ == "__main__":
    scaffold.serve(app)
