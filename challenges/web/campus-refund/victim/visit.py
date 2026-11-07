#!/usr/bin/env python3
"""Hand one URL to the bursar's browser."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_common"))

from victim import visit  # noqa: E402

BURSAR_USERNAME = "bursar"
# Her password IS the challenge flag. It is the same secret the platform's
# admin-bot handler receives at run time (ctx.job.flags). Pass it via env.
BURSAR_PASSWORD = os.environ["FLAG"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--target-url", required=True)
    args = parser.parse_args()

    try:
        visit(args.base_url, args.target_url, BURSAR_USERNAME, BURSAR_PASSWORD)
    except Exception as error:  # noqa: BLE001 - the CLI reports every failure
        print(f"visit: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
