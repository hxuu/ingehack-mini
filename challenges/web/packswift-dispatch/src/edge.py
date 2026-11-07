#!/usr/bin/env python3

from __future__ import annotations

import socket
import socketserver
import sys

APP_HOST = "127.0.0.1"
APP_PORT = 9090
MAX_HEADER = 64 * 1024

FORBIDDEN_BODY = b"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Not available &middot; PackSwift</title>
<link rel="stylesheet" href="/static/fonts/fonts.css">
<link rel="stylesheet" href="/static/skin.css">
</head>
<body>
<div class="b-desk b-desk--tag">
  <div class="b-tag">
    <span class="b-tag-hole" aria-hidden="true"></span>
    <p class="b-tag-brand">PackSwift &middot; edge</p>
    <h1>Refused at edge</h1>
    <p class="b-tag-path">GET /internal/dispatch</p>
    <p>This address is not available to customers. The edge answered this request itself
    and did not pass it to the dispatch application.</p>
    <p class="b-tag-link"><a href="/deploy-log">Deploy log</a></p>
    <span class="b-tag-stamp" aria-hidden="true">403</span>
  </div>
</div>
</body>
</html>
"""


def forbidden_response() -> bytes:
    return (
        b"HTTP/1.1 403 Forbidden\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        b"Content-Length: " + str(len(FORBIDDEN_BODY)).encode() + b"\r\n"
        b"Connection: close\r\n"
        b"\r\n" + FORBIDDEN_BODY
    )


def read_request(sock: socket.socket) -> bytes:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            return b""
        data += chunk
        if len(data) > MAX_HEADER:
            return b""

    head, _, body = data.partition(b"\r\n\r\n")
    length = 0
    for line in head.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            try:
                length = int(value.strip())
            except ValueError:
                length = 0
    while len(body) < length:
        chunk = sock.recv(4096)
        if not chunk:
            break
        body += chunk
    return head + b"\r\n\r\n" + body[:length]


class Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(30)
        raw = read_request(self.request)
        if not raw:
            return

        head, _, body = raw.partition(b"\r\n\r\n")
        lines = head.split(b"\r\n")
        parts = lines[0].split(b" ")
        if len(parts) < 2:
            self.request.sendall(forbidden_response())
            return

        target = parts[1].decode("latin-1", "replace")
        path = target.split("?", 1)[0]
        if path.startswith("/internal/"):
            self.request.sendall(forbidden_response())
            return

        self.forward(lines, body)

    def forward(self, lines: list[bytes], body: bytes) -> None:
        headers = [
            line for line in lines[1:] if not line.lower().startswith(b"connection:")
        ]
        request = (
            b"\r\n".join([lines[0]] + headers + [b"Connection: close"])
            + b"\r\n\r\n"
            + body
        )
        try:
            with socket.create_connection((APP_HOST, APP_PORT), timeout=15) as upstream:
                upstream.sendall(request)
                upstream.shutdown(socket.SHUT_WR)
                while True:
                    chunk = upstream.recv(65536)
                    if not chunk:
                        break
                    self.request.sendall(chunk)
        except OSError as error:
            print(f"edge: application unreachable: {error}", file=sys.stderr)
            self.request.sendall(
                b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            )


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    with Server(("0.0.0.0", 8080), Handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
