#!/usr/bin/env python3
"""Ingehack Mini — hello-shared (static, one shared instance for every team).

The index page keeps a request counter shared across all visitors — visible
proof for players that this is NOT their own copy. The flag is delivered in an
HTTP response header (X-Flag) on /flag, teaching header inspection.
The flag is injected once at deploy time via the FLAG env var.
"""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
FLAG = os.environ.get("FLAG", "ingehack{undeployed}")
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>hello-shared</title>
<style>body{font-family:ui-monospace,monospace;max-width:42em;margin:3em auto;padding:0 1em}
code{background:#eee;padding:.15em .4em}#n{font-size:2em}</style></head>
<body>
<h1>hello-shared</h1>
<p>This server is <strong>shared</strong>: every team in the event loads the
same page right here. Proof — the counter below counts
<em>everyone's</em> requests, and it keeps going up while you read this.</p>
<p>requests served so far: <span id="n">{count}</span></p>
<p>The flag is on another path of this same host — but it does not arrive in
the page body. Use your browser's developer tools (F12) &rarr; Network tab,
request that path, and read the response <em>headers</em>.</p>
</body></html>"""

count = 0


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global count
        if self.path.startswith("/flag"):
            body = b"not in the body this time - check the response headers"
            resp, ctype = 200, "text/plain"
            headers = [("X-Flag", FLAG)]
        else:
            count += 1
            body = PAGE.replace("{count}", f"{count:,}").encode()
            resp, ctype = 200, "text/html"
            headers = []
        self.send_response(resp)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
