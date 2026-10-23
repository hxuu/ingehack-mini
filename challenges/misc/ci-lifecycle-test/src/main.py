import http.server, os

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"scratch challenge proving CI create/delete\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("X-Flag", os.environ.get("FLAG", "no-flag"))
        self.end_headers()
        self.wfile.write(body)
    do_HEAD = do_GET

http.server.HTTPServer(("0.0.0.0", 8080), H).serve_forever()
