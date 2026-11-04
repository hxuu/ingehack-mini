#!/usr/bin/env python3
"""XOR a file with the key of the SSH session it is running in.

Usage: encode.py <input> [output] [--key <material>]

The key is the client port of the current session, taken from the
SSH_CLIENT variable that sshd exports into every login shell. Two logins
never share a port, so the same file encodes differently each time --
and the blob is useless without the session it came from.
"""
import argparse
import os
import sys


def session_key() -> bytes:
    client = os.environ.get("SSH_CLIENT", "").split()
    if len(client) < 2:
        sys.exit("encode.py: no SSH session (SSH_CLIENT unset); pass --key")
    return client[1].encode()


def encode(data: bytes, key: bytes) -> str:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data)).hex()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outfile", nargs="?")
    ap.add_argument("--key", help="repeating key material for an offline re-run")
    args = ap.parse_args()

    key = args.key.encode() if args.key else session_key()
    with open(args.infile, "rb") as f:
        data = f.read()

    out = args.outfile or args.infile + ".enc"
    with open(out, "w") as f:
        f.write(encode(data, key) + "\n")


if __name__ == "__main__":
    main()
