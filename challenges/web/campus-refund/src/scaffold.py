"""Shared plumbing for every record. Keep this small."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask, render_template, render_template_string

_SOURCE_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Source</title></head>
<body>
<h1>Source</h1>
<p>The application's own source, exactly as it runs.</p>
{% for file in files %}
<h2>{{ file.name }}</h2>
<pre>{% for number, line in file.lines %}{{ number }} | {{ line }}
{% endfor %}</pre>
{% endfor %}
<footer><a href="/">home</a></footer>
</body>
</html>
"""


def read_flag() -> str:
    """Read the flag injected at container start; fail loudly when it is absent."""
    flag = os.environ.get("FLAG", "").strip()
    if not flag:
        raise RuntimeError(
            "FLAG is not set. Start the container with -e FLAG=ingehack{...}; "
            "the flag never lives in the source."
        )
    return flag


def mint() -> str:
    """A random per-boot secret.

    Anything the challenge must keep secret (session keys, demo passwords,
    agent tokens) is minted here at start-up and shown only where it is
    meant to travel (the login page, the desk cookie). Reading the source
    reveals the plumbing, never a usable credential.
    """
    return secrets.token_urlsafe(18)


def register_health(app: Flask) -> None:
    """Expose an unauthenticated liveness check on /_health."""

    @app.get("/_health")
    def _health():
        return "ok"


def register_source(app: Flask, files: list[str], template: str | None = None) -> None:
    """Serve the named text files from /src with line numbers, never the flag."""
    app_dir = Path(__file__).resolve().parent

    @app.get("/src")
    def _source():
        rendered = []
        for name in files:
            lines = (app_dir / name).read_text(encoding="utf-8").splitlines()
            rendered.append({"name": name, "lines": list(enumerate(lines, 1))})
        if template:
            return render_template(template, files=rendered)
        return render_template_string(_SOURCE_PAGE, files=rendered)


def serve(app: Flask) -> None:
    """Serve one process, threaded, so in-memory state is shared by all requests."""
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)

