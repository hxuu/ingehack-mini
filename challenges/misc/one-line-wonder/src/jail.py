#!/usr/bin/env python3
"""One-line Python jail: empty builtins, a substring blacklist, and an audit
hook that guards the real flag."""
import os
import sys
import unicodedata

FLAG_PATH = "/flag.txt"
MAX_LEN = 90
BANNED = (
    "import",
    "os",
    "sys",
    "open",
    "eval",
    "exec",
    "__",
    "subclasses",
    "globals",
    "flag",
)

_inside_hook = False


def _audit(event, args):
    """Deny opening the real flag, but nothing else."""
    global _inside_hook
    if event != "open" or _inside_hook:
        return
    path = args[0]
    if isinstance(path, int):
        return
    if isinstance(path, bytes):
        try:
            path = path.decode()
        except UnicodeDecodeError:
            return
    _inside_hook = True
    try:
        if os.path.realpath(path) == FLAG_PATH:
            raise PermissionError
    finally:
        _inside_hook = False


def main():
    sys.addaudithook(_audit)
    sys.stdout.write("line> ")
    sys.stdout.flush()

    raw = sys.stdin.readline(4096)
    if not raw:
        return
    line = raw.rstrip("\r\n")

    if len(line) > MAX_LEN or any(word in line for word in BANNED):
        print("blocked")
        return

    # Normalize only after the filter has seen the raw input. This is the
    # step that makes the filter look stricter than it is.
    line = unicodedata.normalize("NFKC", line)

    try:
        value = eval(line, {"__builtins__": {}}, {})
        if value is not None:
            print(value)
    except BaseException:
        print("blocked")


if __name__ == "__main__":
    main()
