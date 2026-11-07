import urllib.parse

import scaffold
from flask import Flask, abort, render_template, request

app = Flask(__name__)
FLAG = scaffold.read_flag()


@app.errorhandler(404)
def not_found(error):
    return render_template("notfound.html"), 404


scaffold.register_health(app)
scaffold.register_source(app, ["app.py", "edge.py"], template="source.html")


def path_as_requested() -> str:
    raw = request.environ.get("RAW_URI") or request.full_path
    return urllib.parse.unquote(raw.split("?", 1)[0])


@app.get("/", defaults={"rest": ""})
@app.get("/<path:rest>")
def page(rest: str):
    path = path_as_requested()
    if path == "/":
        return render_template("home.html")
    if path == "/deploy-log":
        return render_template("deploy_log.html")
    if path == "/internal/dispatch":
        return render_template("dispatch.html", flag=FLAG)
    abort(404)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9090, threaded=True, use_reloader=False)
