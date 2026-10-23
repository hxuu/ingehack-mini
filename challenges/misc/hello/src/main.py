#!/usr/bin/env python3
"""Ingehack Mini — hello (static sanity challenge).

Serves a beginner instructions page and hands over the flag on a plain path.
The flag is injected once at deploy time via the FLAG env var.
"""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
FLAG = os.environ.get("FLAG", "ingehack{undeployed}")
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>hello</title>
<style>body{font-family:ui-monospace,monospace;max-width:42em;margin:3em auto;padding:0 1em}
code{background:#eee;padding:.15em .4em}</style></head>
<body>
<h1>hello — your first flag</h1>
<p>This is a plain HTTP endpoint like any website you visit. Your browser sent a
<code>GET</code> request and this server answered with this page.</p>
<ol>
<li>Open your browser's developer tools (F12), <strong>Network</strong> tab,
and reload — see the request your browser made and this response.</li>
<li>To <em>read</em> a different part of the response, try a different path —
append <code>/flag</code> to the URL in the address bar and hit Enter.</li>
<li>Copy what you find there, paste it into the flag box for this challenge on
the platform, and submit.</li>
</ol>
<p>The flag stays intact for every team here: this challenge is shared, not
instanced. Read more in the platform's challenge description.</p>
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
