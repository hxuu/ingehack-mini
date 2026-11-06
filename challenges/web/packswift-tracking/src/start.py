#!/usr/bin/env python3
"""Start the tracking application, wait for it, then start the edge."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import edge

HERE = Path(__file__).resolve().parent


def wait_for_app(timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", 9090), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main() -> int:
    app = subprocess.Popen([sys.executable, str(HERE / "app.py")])
    try:
        if not wait_for_app():
            print("start: the application did not answer on 127.0.0.1:9090", file=sys.stderr)
            return 1
        edge.main()
        return 0
    finally:
        if app.poll() is None:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()


if __name__ == "__main__":
    raise SystemExit(main())
