#!/usr/bin/env python3
"""Ingehack Mini — hello-instancer (instanced sanity challenge).

Each team gets its own copy of this container, started on demand. The
instancer bakes the team's flag in via the RCTF_FLAG env variable — this code
is identical for everyone, yet every team sees a *different* flag on /flag.
"""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 80
FLAG = os.environ.get("RCTF_FLAG", "ingehack{no_team_no_flag}")
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>hello-instancer</title>
<style>body{font-family:ui-monospace,monospace;max-width:42em;margin:3em auto;padding:0 1em}</style>
</head><body>
<h1>hello-instancer — an instance just for you</h1>
<p>You (or the button on the platform) asked for a <em>copy</em> of this
challenge, and the CTF infra started one just for you — with an isolated
container, its own network, and its own flag.</p>
<ol>
<li>Verification and isolation live here too: <strong>verify</strong> by
loading <code>/flag</code> on this host.</li>
<li>Each team gets a different flag here, because each copy is baked at
launch.</li>
<li>Note the host in your address bar: it is one instance host per team.</li>
</ol>
<p>Done? Submit your flag on the platform. The plan keeps running for you; the
answer stays stable.</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/flag"):
            body = FLAG.encode()
            ctype = "text/plain"
        else:
            body = PAGE.encode()
            ctype = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
