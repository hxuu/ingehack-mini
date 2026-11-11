#!/usr/bin/env python3
"""ch41n.py — one Cutout process (P1..P6), run as user ch41n.

argv: ch41n.py <LABEL>      (LABEL = random 8-hex id chosen at build time)

Behavior (per spec):
  * fragment  /home/ch41n/fragments/<LABEL>   (0600)
  * unlock    /home/ch41n/unlocks/<LABEL>     (0600)
  * role comes from the world-readable ledger /var/lib/vendor-tool/.ledger
        <LABEL> <offset> <purpose>            purpose: fragment | key
    purpose == "key"   -> blob at OFFSET xored with the combined /opt key
                          (first line of lib/.part1 + share/.part2)
    purpose != "key" and fragment does not start with "ingehack{"
                       -> 4096-byte random blob, fragment xored at OFFSET
                          with the REAL key
    otherwise          -> plaintext fragment straight onto fd 3
  * blob/plaintext body is written to a temp file, fd 3 is opened read-only
    on it, the file is unlinked — fd 3 is the only remaining handle.
  * loop: poll /tmp/<LABEL>.trigger every 100 ms. On a payload equal to the
    unlock code: fchmod(fd3, 0644), notify the root handoff service via
    /run/cutout/<LABEL>.unlock ("<pid>\\n" — pid only, no secrets), sleep(10),
    fchmod(fd3, 0600), unlink trigger. Poll again.

No fragment, key or offset appears in argv, the environment, or any
world-readable file. Only labels, pids and window-boundaries are public.
"""
import os
import socket
import struct
import sys
import time
import tempfile

BASE = "/home/ch41n"
LEDGER = "/var/lib/vendor-tool/.ledger"
SOCK_DIR = "/tmp/.cutout"
TRIGGER_DIR = "/tmp"
WINDOW = 10
REAL_KEY = b"r34l_k3y_0bs1d14n"     # the key xored under P6, out of /opt flow


def die(msg):
    print(f"ch41n[{LABEL}]: {msg}", file=sys.stderr)
    sys.exit(1)


def xor_into(blob, payload, key, offset):
    for i, b in enumerate(payload):
        blob[offset + i] = b ^ key[i % len(key)]


def ledger_row(label):
    with open(LEDGER, "rb") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith(b"#"):
                continue
            parts = line.split()
            if len(parts) == 3 and parts[0].decode() == label:
                return int(parts[1]), parts[2].decode()
    return None


def stage_fd3(body):
    """Write `body` to a temp file, open fd 3 read-only on it, unlink."""
    tmpfd, tmppath = tempfile.mkstemp(prefix=f".{LABEL}-", dir="/tmp")
    os.write(tmpfd, body)
    os.close(tmpfd)
    fd3 = os.open(tmppath, os.O_RDONLY, 0o600)
    os.unlink(tmppath)
    if fd3 != 3:
        os.dup2(fd3, 3)
        os.close(fd3)
        fd3 = 3
    return fd3


def main():
    global LABEL
    if len(sys.argv) != 2:
        die(f"usage: ch41n.py <LABEL> (got {sys.argv[1:]!r})")
    LABEL = sys.argv[1]

    row = ledger_row(LABEL)
    if row is None:
        die(f"no ledger row for {LABEL}")
    offset, purpose = row

    with open(f"{BASE}/fragments/{LABEL}", "rb") as fh:
        frag = fh.read()
    with open(f"{BASE}/unlocks/{LABEL}") as fh:
        unlock = fh.read().strip()

    if purpose == "key":
        k1 = open("/opt/vendor-tool/lib/.part1").readline().strip()
        k2 = open("/opt/vendor-tool/share/.part2").readline().strip()
        outer = (k1 + k2).encode()      # 18 bytes: v3rm1l10n0bs1d14n
        payload = frag                  # the pending real key
    elif not frag.startswith(b"ingehack{"):
        outer = REAL_KEY                # P4 / P5 wrap under the real key
        payload = frag
        if offset + len(payload) > 4096:
            die("blob offset overflow")
    else:
        outer = None                    # P1 / P2 / P3 stay plaintext
        payload = frag

    if outer is None:
        body = payload
    else:
        blob = bytearray(os.urandom(4096))
        xor_into(blob, payload, outer, offset)
        body = bytes(blob)

    fd3 = stage_fd3(body)

    while True:
        trig = f"{TRIGGER_DIR}/{LABEL}.trigger"
        try:
            with open(trig, "rb") as fh:
                data = fh.read().strip()
        except OSError:
            time.sleep(0.1)
            continue
        if data != unlock.encode():
            time.sleep(0.1)
            continue

        try:
            os.fchmod(fd3, 0o644)
        except OSError:
            pass
        # hand the fd to the player-uid keeper over SCM_RIGHTS (kernel-level
        # dup — no ptrace, no capabilities). Keeper exposes it at
        # /proc/<its-pid>/fd/3 while this inode is 0644.
        sent = False
        try:
            sk = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sk.connect(f"{SOCK_DIR}/{LABEL}.sock")
            sk.sendmsg([b"fd"], [
                (socket.SOL_SOCKET, socket.SCM_RIGHTS,
                 struct.pack("i", fd3))])
            sk.close()
            sent = True
        except OSError:
            pass

        time.sleep(WINDOW)

        try:
            os.fchmod(fd3, 0o600)
        except OSError:
            pass
        try:
            os.unlink(trig)          # one-shot trigger, per spec
        except OSError:
            pass
        if not sent:
            time.sleep(1.0)   # keeper unreachable; the trigger was consumed


if __name__ == "__main__":
    main()
