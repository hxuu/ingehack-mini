"""Vault Co. login portal - intentionally vulnerable training challenge.

Concept: anything sent to the browser is visible to the visitor. The admin
credentials and two of the three flag fragments ship in client-side files.
See ../solution/SOLUTION.md for the intended solution and the fix.
"""

import os

from flask import Flask, Response, render_template, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Static files are served by explicit routes so /static/app.js can be
# generated from a template (it needs the environment-provided flag fragment).
app = Flask(__name__, static_folder=None)

FLAG = os.environ.get("FLAG", "ingehack{undeployed}")


def split_flag(flag):
    """Split the flag into three fragments, one for each hiding place."""
    third = len(flag) // 3
    return flag[:third], flag[third : 2 * third], flag[2 * third :]


FLAG_PART_1, FLAG_PART_2, FLAG_PART_3 = split_flag(FLAG)

# Demo admin account. These same values are hardcoded in /static/app.js.
ADMIN_USER = "admin"
ADMIN_PASSWORD = "vault-admin-2024"


@app.get("/")
def index():
    return render_template("index.html", part1=FLAG_PART_1)


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username == ADMIN_USER and password == ADMIN_PASSWORD:
        # Only a successful server-side check reveals the final fragment.
        return render_template(
            "index.html", part1=FLAG_PART_1, flag_part=FLAG_PART_3
        )

    return (
        render_template(
            "index.html",
            part1=FLAG_PART_1,
            error="Invalid username or password.",
        ),
        401,
    )


@app.get("/static/app.js")
def app_js():
    # VULN: the admin password and the second flag fragment are embedded in
    # JavaScript sent to every visitor. Viewing the source reveals both.
    js = render_template("app.js", part2=FLAG_PART_2)
    return Response(js, mimetype="application/javascript")


@app.get("/static/style.css")
def style_css():
    return send_from_directory(
        os.path.join(BASE_DIR, "static"), "style.css", mimetype="text/css"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
