#!/usr/bin/env python3
"""Ingehack Mini — sanity-check-2 (static; flag lives in the committed handout).

Deployed only so the static-challenge path has something to answer with; the
actual challenge artifact is the local attachment (files/naughty-list.zip)
that register uploads at CI time. No flag in the container on purpose.
"""
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>sanity-check-2</title>
<style>body{font-family:ui-monospace,monospace;max-width:42em;margin:3em auto;padding:0 1em}
code{background:#eee;padding:.15em .4em}</style></head>
<body>
<h1>sanity-check-2 — attached, part 1</h1>
<p>The flag is not on this page. It is inside <code>naughty-list.zip</code>,
attached to this challenge on the platform — download it under <strong>Files</strong>,
unzip it, read the top of the list.</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE.encode())

    do_HEAD = do_GET


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
