#!/usr/bin/env python3
"""Open one ticket in the support agent's browser."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_common"))

from victim import visit  # noqa: E402

AGENT_USERNAME = "agent"
AGENT_PASSWORD = os.environ["FLAG"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--target-url", required=True)
    args = parser.parse_args()

    try:
        visit(args.base_url, args.target_url, AGENT_USERNAME, AGENT_PASSWORD)
    except Exception as error:  # noqa: BLE001 - the CLI reports every failure
        print(f"visit: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
