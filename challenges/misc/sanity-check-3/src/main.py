#!/usr/bin/env python3
"""Ingehack Mini — sanity-check-3 (static; flag lives in an R2-hosted handout).

Deployed only so the static-challenge path has something to answer with; the
actual challenge artifact (gifts.zip) lives in the attachments bucket and is
referenced by URL in chall.yaml. No flag in the container on purpose.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>sanity-check-3</title>
<style>body{font-family:ui-monospace,monospace;max-width:42em;margin:3em auto;padding:0 1em}
code{background:#eee;padding:.15em .4em}</style></head>
<body>
<h1>sanity-check-3 — attached, part 2</h1>
<p>The flag is not on this page, and this time the attachment did not come
from the challenge repo either: <code>gifts.zip</code> lives in the event's
attachment bucket. Grab it under <strong>Files</strong> on the platform,
open the archive, and pay attention to how the crates are numbered.</p>
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
