#!/usr/bin/env python3
"""Run one authored web challenge solver with a team token and a challenge id.

Examples:
  python3 challenges/web/solve.py --token "$TEAM_TOKEN" --challenge course-finder
  python3 challenges/web/solve.py --token "$TEAM_TOKEN" \
      "https://ctf.ingeniums.club/challenges?challenge=course-finder"

The runner maps the live challenge id to its directory, resolves the public
challenge host (or lets the challenge solver start its own instance), then
calls that challenge's solution/solve.py. The flag is printed on stdout and
progress stays on stderr.

The token is a player API token. It is only required for the three admin-bot
challenges and for the instanced challenge, because those call the platform.
The static challenges need only the challenge id.

Supported challenges:

  el-minha             El Minha              admin bot
  course-finder        Course Finder         admin bot
  open-ticket          Open Ticket           admin bot
  dispatch             Dispatch              static
  the-doorman          The Doorman           static
  packswift-tracking   Where Requests End    instanced
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PLATFORM = "https://ctf.ingeniums.club"
DEFAULT_HOST_SUFFIX = "challs.ingeniums.club"
HTTPS_PORT = 9488


@dataclass(frozen=True)
class Challenge:
    """One live challenge and the solver that proves it."""

    live_id: str
    title: str
    directory: str
    kind: str  # "bot", "static", or "instanced"


CHALLENGES = {
    "el-minha": Challenge("el-minha", "El Minha", "campus-refund", "bot"),
    "course-finder": Challenge("course-finder", "Course Finder", "faculty-finder", "bot"),
    "open-ticket": Challenge("open-ticket", "Open Ticket", "helpdesk-thread", "bot"),
    "dispatch": Challenge("dispatch", "Dispatch", "packswift-dispatch", "static"),
    "the-doorman": Challenge("the-doorman", "The Doorman", "packswift-doorman", "static"),
    "packswift-tracking": Challenge(
        "packswift-tracking", "Where Requests End", "packswift-tracking", "instanced"
    ),
}


def solver_path(challenge: Challenge) -> Path:
    """Return the challenge's own solution/solve.py."""
    return Path(__file__).resolve().parent / challenge.directory / "solution" / "solve.py"


def parse_challenge(value: str) -> tuple[str, str | None]:
    """Return (challenge id, platform origin) from a bare id or a challenge URL."""
    value = value.strip()
    if "://" not in value:
        return value, None

    parsed = urllib.parse.urlparse(value)
    ids = urllib.parse.parse_qs(parsed.query).get("challenge")
    if ids:
        return ids[0], f"{parsed.scheme}://{parsed.netloc}"

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "challenges":
        return parts[1], f"{parsed.scheme}://{parsed.netloc}"

    raise SystemExit(
        "solver: cannot find ?challenge=<id> in the URL; "
        "pass the id directly instead, for example --challenge course-finder"
    )


def find_challenge(value: str) -> Challenge:
    """Look up a challenge by live id or by title."""
    challenge_id, _ = parse_challenge(value)
    challenge = CHALLENGES.get(challenge_id.strip().lower())
    if challenge:
        return challenge

    title = value.strip().lower()
    for candidate in CHALLENGES.values():
        if candidate.title.lower() == title:
            return candidate

    known = ", ".join(sorted(CHALLENGES))
    raise SystemExit(f"solver: unknown challenge {value!r}; known challenges: {known}")


def resolve_token(args: argparse.Namespace) -> str | None:
    """Read the player token from --token, --token-file, or RCTF_TOKEN."""
    if args.token:
        return args.token.strip()
    if args.token_file:
        try:
            return Path(args.token_file).read_text(encoding="utf-8").strip()
        except OSError as error:
            raise SystemExit(f"solver: cannot read the token file: {error}") from error
    token = os.environ.get("RCTF_TOKEN")
    return token.strip() if token else None


def static_base(challenge: Challenge, host_suffix: str) -> str:
    """Return the challenge's public HTTPS base URL."""
    return f"https://{challenge.directory}.{host_suffix}:{HTTPS_PORT}/"


def build_command(
    challenge: Challenge,
    args: argparse.Namespace,
    token: str | None,
    platform_url: str,
    base_url: str | None,
) -> list[str]:
    """Build the argv for the challenge's own solver."""
    solver = solver_path(challenge)
    if not solver.is_file():
        raise SystemExit(f"solver: missing solver for {challenge.live_id}: {solver}")

    # A dry run only shows the command, so a missing token is not an error there.
    if args.dry_run:
        token = token or "<token>"

    if challenge.kind == "bot":
        if args.stage not in ("all", "prepare", "submit"):
            raise SystemExit("solver: --stage must be all, prepare, or submit")
        if args.stage == "submit" and not args.claim:
            raise SystemExit("solver: --stage submit needs --claim from --stage prepare")
        if args.stage == "all" and not token:
            raise SystemExit(
                "solver: --stage all needs a player token; pass --token, "
                "--token-file, or set RCTF_TOKEN"
            )
        command = [
            sys.executable,
            str(solver),
            "--base-url",
            base_url or static_base(challenge, args.host_suffix),
            "--stage",
            args.stage,
            "--challenge-id",
            challenge.live_id,
        ]
        if args.stage == "all":
            command += ["--platform-url", platform_url, "--token", token or ""]
        if args.stage == "submit":
            command += ["--claim", args.claim or ""]
        return command

    if challenge.kind == "static":
        return [
            sys.executable,
            str(solver),
            "--base-url",
            base_url or static_base(challenge, args.host_suffix),
        ]

    if challenge.kind == "instanced":
        if base_url:
            return [sys.executable, str(solver), "--base-url", base_url]
        if not token:
            raise SystemExit(
                "solver: starting the instance needs a player token; pass --token, "
                "--token-file, or set RCTF_TOKEN"
            )
        return [
            sys.executable,
            str(solver),
            "--platform-url",
            platform_url,
            "--token",
            token,
            "--challenge-id",
            challenge.live_id,
        ]

    raise SystemExit(f"solver: unknown solver kind for {challenge.live_id}: {challenge.kind}")


def stop_instance(platform_url: str, token: str, challenge_id: str) -> None:
    """Stop the team's instance after a successful instanced solve."""
    request = urllib.request.Request(
        f"{platform_url.rstrip('/')}/api/v2/integrations/challs/{challenge_id}/instance",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "ingehack-solver/1.0",
        },
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response).get("data") or {}
        print(f"instance: {data.get('status', 'stopped')}", file=sys.stderr)
    except urllib.error.URLError as error:
        print(f"solver: could not stop the instance: {error}", file=sys.stderr)


def redact(command: list[str]) -> list[str]:
    """Hide the token value in a command line printed by --dry-run."""
    redacted: list[str] = []
    for index, part in enumerate(command):
        if index > 0 and command[index - 1] == "--token":
            redacted.append("<token>")
        else:
            redacted.append(part)
    return redacted


def run(command: list[str]) -> int:
    """Run the solver, pass its output through, and return its exit code."""
    try:
        result = subprocess.run(command, text=True, capture_output=True)
    except OSError as error:
        print(f"solver: cannot run the challenge solver: {error}", file=sys.stderr)
        return 1

    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.stdout:
        print(result.stdout, end="")
    return result.returncode


def list_challenges() -> None:
    """Print the supported challenge ids and their solver paths."""
    root = Path(__file__).resolve().parent
    for challenge in sorted(CHALLENGES.values(), key=lambda item: item.live_id):
        path = solver_path(challenge).relative_to(root)
        print(f"{challenge.live_id:22} {challenge.title:20} {challenge.kind:10} {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  %(prog)s --token "$TEAM_TOKEN" --challenge course-finder\n'
            '  %(prog)s --token "$TEAM_TOKEN" \\\n'
            '      "https://ctf.ingeniums.club/challenges?challenge=course-finder"\n'
            '  %(prog)s --list\n'
        ),
    )
    parser.add_argument(
        "challenge",
        nargs="?",
        help="challenge id or full challenge URL, for example course-finder",
    )
    parser.add_argument(
        "--challenge",
        dest="challenge_option",
        metavar="ID_OR_URL",
        help="challenge id or full challenge URL (same as the positional form)",
    )
    parser.add_argument(
        "--token",
        help="player API token; can also come from RCTF_TOKEN or --token-file",
    )
    parser.add_argument("--token-file", help="file containing the player API token")
    parser.add_argument(
        "--platform-url",
        help=f"platform base URL (default: {DEFAULT_PLATFORM}, or the URL origin)",
    )
    parser.add_argument(
        "--base-url",
        help="override the challenge base URL, useful for local containers",
    )
    parser.add_argument(
        "--host-suffix",
        default=DEFAULT_HOST_SUFFIX,
        help=f"challenge host suffix (default: {DEFAULT_HOST_SUFFIX})",
    )
    parser.add_argument(
        "--stage",
        choices=("all", "prepare", "submit"),
        default="all",
        help="admin-bot stage (default: all; prepare and submit are for reviews)",
    )
    parser.add_argument(
        "--claim",
        help="claim code from --stage prepare, needed for --stage submit",
    )
    parser.add_argument(
        "--stop-instance",
        action="store_true",
        help="stop the instanced challenge after a successful solve",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the resolved solver command without running it",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list the supported challenges and exit",
    )
    args = parser.parse_args()

    if args.list:
        list_challenges()
        return 0

    if args.challenge and args.challenge_option:
        parser.error("pass the challenge once, either positionally or with --challenge")

    value = args.challenge_option or args.challenge
    if not value:
        parser.error("pass a challenge id or URL, or use --list")

    challenge = find_challenge(value)
    _, url_platform = parse_challenge(value)
    platform_url = (args.platform_url or url_platform or DEFAULT_PLATFORM).rstrip("/")

    if args.stage != "all" and challenge.kind != "bot":
        parser.error("--stage only applies to the admin-bot challenges")
    if args.claim and not (challenge.kind == "bot" and args.stage == "submit"):
        parser.error("--claim only applies with --stage submit on an admin-bot challenge")

    token = resolve_token(args)
    base_url = args.base_url.rstrip("/") if args.base_url else None
    command = build_command(challenge, args, token, platform_url, base_url)

    if args.dry_run:
        print(f"challenge: {challenge.live_id} ({challenge.title})")
        print(f"kind: {challenge.kind}")
        print(f"platform: {platform_url}")
        if base_url:
            print(f"base url: {base_url}")
        elif challenge.kind == "instanced":
            print("base url: started by the solver")
        else:
            print(f"base url: {static_base(challenge, args.host_suffix)}")
        print("command: " + " ".join(shlex.quote(part) for part in redact(command)))
        return 0

    return_code = run(command)
    if (
        return_code == 0
        and args.stop_instance
        and challenge.kind == "instanced"
        and not base_url
        and token
    ):
        stop_instance(platform_url, token, challenge.live_id)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
