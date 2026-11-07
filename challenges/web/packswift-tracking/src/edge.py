#!/usr/bin/env python3
"""PackSwift tracking edge: owns port 8080 and forwards to the tracking application."""

from __future__ import annotations

import socket
import socketserver
import sys

import skin

APP_HOST = "127.0.0.1"
APP_PORT = 9090
MAX_HEADER = 64 * 1024


def edge_refusal(status: int, path: str = "/track") -> bytes:
    """A refusal body from the same drawing set the application serves."""
    if status == 403:
        body = skin.edge_page(
            title="Not available · PackSwift Tracking",
            sheet_no="04",
            kicker="EXCEPTION &middot; ANSWERED AT THE EDGE",
            heading="Not available",
            path=f"GET {path}",
            paragraph=(
                "This address is not available to customers. The edge answered this "
                "request itself and did not pass it to the tracking application."
            ),
            stamp_label="EDGE 403",
            stamp_sub="NOT FORWARDED",
            note_heading="MARGIN NOTE 5",
            note_text=(
                '"Not forwarded" is a fact about this request, not about the address.'
            ),
        )
        return page(403, "Forbidden", body)

    body = skin.edge_page(
        title="Not accepted · PackSwift Tracking",
        sheet_no="05",
        kicker="EXCEPTION &middot; ANSWERED AT THE EDGE",
        heading="Not accepted",
        path=f"POST {path} (Content-Length twice)",
        paragraph=(
            "This request carried more than one length header. The edge stopped it "
            "here and did not pass it to the tracking application."
        ),
        stamp_label="EDGE 400",
        stamp_sub="TWO LENGTHS",
        note_heading="MARGIN NOTE 6",
        note_text=(
            "The edge counts lengths. The application counts bytes. Those are not "
            "the same job."
        ),
    )
    return page(400, "Bad Request", body)


def page(status: int, reason: str, body: str) -> bytes:
    data = body.encode("utf-8")
    return (
        f"HTTP/1.1 {status} {reason}\r\n".encode()
        + b"Content-Type: text/html; charset=utf-8\r\n"
        + b"Content-Length: " + str(len(data)).encode() + b"\r\n"
        + b"Connection: close\r\n"
        + b"\r\n"
        + data
    )


class Reader:
    """A small buffered reader so chunk framing and header reads share one buffer."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buffer = b""

    def _fill(self) -> None:
        chunk = self.sock.recv(65536)
        if not chunk:
            raise EOFError
        self.buffer += chunk

    def read_until(self, marker: bytes) -> bytes:
        while marker not in self.buffer:
            if len(self.buffer) > MAX_HEADER:
                raise ValueError("header too large")
            self._fill()
        end = self.buffer.index(marker) + len(marker)
        out, self.buffer = self.buffer[:end], self.buffer[end:]
        return out

    def read_exact(self, count: int) -> bytes:
        while len(self.buffer) < count:
            self._fill()
        out, self.buffer = self.buffer[:count], self.buffer[count:]
        return out

    def read_line(self) -> bytes:
        return self.read_until(b"\r\n")


def read_chunked(reader: Reader) -> bytes:
    """Read a chunked body to its end and return the raw bytes, framing included."""
    raw = b""
    while True:
        line = reader.read_line()
        raw += line
        try:
            size = int(line.split(b";", 1)[0].strip(), 16)
        except ValueError:
            raise ValueError("bad chunk size") from None
        if size == 0:
            while True:
                trailer = reader.read_line()
                raw += trailer
                if trailer == b"\r\n":
                    return raw
        raw += reader.read_exact(size)
        raw += reader.read_exact(2)


def parse_head(head: bytes) -> tuple[bytes, list[bytes], list[tuple[bytes, bytes]]]:
    lines = head.split(b"\r\n")
    request_line = lines[0]
    header_lines = lines[1:]
    parsed = []
    for line in header_lines:
        name, separator, value = line.partition(b":")
        if separator:
            parsed.append((name.strip().lower(), value.strip()))
    return request_line, header_lines, parsed


def read_request(sock: socket.socket):
    """Read one request. Return (request, None) or (None, refusal) for a bad one."""
    reader = Reader(sock)
    head = reader.read_until(b"\r\n\r\n")[:-4]
    request_line, header_lines, parsed = parse_head(head)

    lengths = [value for name, value in parsed if name == b"content-length"]
    if len(lengths) > 1:
        return None, edge_refusal(400)

    transfer = b",".join(value for name, value in parsed if name == b"transfer-encoding")
    if b"chunked" in transfer.lower():
        try:
            raw_body = read_chunked(reader)
        except (EOFError, ValueError):
            return None, edge_refusal(400)
    else:
        try:
            length = int(lengths[0]) if lengths else 0
        except ValueError:
            length = 0
        try:
            raw_body = reader.read_exact(length) if length else b""
        except EOFError:
            return None, edge_refusal(400)

    return (request_line, header_lines, raw_body), None


class Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(30)
        try:
            request, refusal = read_request(self.request)
        except (EOFError, ValueError, OSError):
            return
        if refusal is not None:
            self.request.sendall(refusal)
            return

        request_line, header_lines, raw_body = request
        parts = request_line.split(b" ")
        if len(parts) < 2:
            self.request.sendall(edge_refusal(400))
            return

        target = parts[1].decode("latin-1", "replace")
        path = target.split("?", 1)[0]
        if path.startswith("/internal/"):
            self.request.sendall(edge_refusal(403, path))
            return

        self.forward(request_line, header_lines, raw_body)

    def forward(self, request_line: bytes, header_lines: list[bytes], raw_body: bytes) -> None:
        chunked = any(
            line.partition(b":")[0].strip().lower() == b"transfer-encoding"
            and b"chunked" in line.partition(b":")[2].lower()
            for line in header_lines
        )
        headers = []
        for line in header_lines:
            name = line.partition(b":")[0].strip().lower()
            if name == b"x-packswift-role":
                continue
            if name == b"connection" and not chunked:
                continue
            headers.append(line)
        if not chunked:
            headers.append(b"Connection: close")

        request = b"\r\n".join([request_line] + headers) + b"\r\n\r\n" + raw_body
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
