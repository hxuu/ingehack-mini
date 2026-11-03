#!/usr/bin/env python3
"""Ingehack Mini — sanity-check (the welcome challenge, shared static).

Serves a welcome page and hands over the flag on a plain path. Worth 0 points;
the point is to teach the request/response loop before the event gets hard.
The flag is injected once at deploy time via the FLAG env var.
"""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
FLAG = os.environ.get("FLAG", "ingehack{undeployed}")
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>welcome</title>
<style>body{font-family:ui-monospace,monospace;max-width:42em;margin:3em auto;padding:0 1em}
code{background:#eee;padding:.15em .4em}</style></head>
<body>
<h1>Welcome to Ingehack Mini</h1>
<p>This is a real website answering a real request: your browser sent a
<code>GET</code> request for <code>/</code> and this server answered with this
page. That exchange, request and response, is the whole game.</p>
<ol>
<li>Open your browser's developer tools (F12), switch to the
<strong>Network</strong> tab, and reload. You will see the request above and
this page coming back.</li>
<li>The flag is served on a different path of this same host. Try adding
<code>/flag</code> to the URL in the address bar and hit Enter.</li>
<li>Copy what you find there, paste it into the flag box for this challenge on
the platform, and submit.</li>
</ol>
<p>This challenge is shared and worth 0 points — nobody's score depends on
you finishing it in a hurry. Ask a mentor if anything is unclear, and enjoy
the event.</p>
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
