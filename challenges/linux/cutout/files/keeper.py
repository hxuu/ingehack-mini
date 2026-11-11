#!/usr/bin/env python3
"""keeper.py — Cutout fd holder, runs as boul3h14 (one per process label).

The daemon (ch41n) fchmods its fd to 0644 inside the unlock window and hands
the already-open fd to this keeper over an AF_UNIX SCM_RIGHTS datagram. The
keeper dup2s it onto a permanent fd 3, so /proc/<keeper-pid>/fd/3 is owned by
the PLAYER uid and is readable (same-uid rule) exactly while the underlying
inode is world-readable. Unix fd-passing is a kernel-level dup — no ptrace
involved, no capabilities required.

Files it manages (all pid-only, no secrets):
  /run/cutout/<LABEL>.holder   <- written ONCE at startup: this keeper's pid
"""
import os
import socket
import struct
import sys
import time

NOTIFY_DIR = "/run/cutout"
SOCK_DIR = "/tmp/.cutout"
KNOWN_FD = 3            # permanent holding slot
HOLD_SECONDS = 12       # > the daemon's 10 s chmod window


def main():
    label = sys.argv[1]

    # holder pid is public and static for the life of the instance
    try:
        with open(f"{NOTIFY_DIR}/{label}.holder", "w") as fh:
            fh.write(f"{os.getpid()}\n")
        os.chmod(f"{NOTIFY_DIR}/{label}.holder", 0o644)
    except OSError:
        pass

    os.makedirs(SOCK_DIR, exist_ok=True)
    path = f"{SOCK_DIR}/{label}.sock"
    try:
        os.unlink(path)
    except OSError:
        pass
    # Placeholder on the lowest free fd so the listening socket lands above
    # KNOWN_FD — otherwise dup2(incoming_fd, 3) closes the server socket
    # after the very first handoff and every later send is ECONNREFUSED.
    placeholder = os.open(os.devnull, os.O_RDONLY)  # fd 3
    assert placeholder == KNOWN_FD, placeholder

    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(path)
    os.chmod(path, 0o666)

    while True:
        # blocking receive; each message carries one SCM_RIGHTS fd
        try:
            data, ancdata, _flags, _addr = server.recvmsg(
                256, socket.CMSG_SPACE(4))
        except OSError:
            time.sleep(0.2)
            continue
        fd = None
        for level, ctype, cdata in ancdata:
            if level == socket.SOL_SOCKET and ctype == socket.SCM_RIGHTS:
                fd = struct.unpack("i", cdata[:4])[0]
        if fd is None:
            continue
        if fd != KNOWN_FD:
            os.dup2(fd, KNOWN_FD)     # fd 3 now shares the daemon's inode
            os.close(fd)
        time.sleep(HOLD_SECONDS)  # window long outlives the daemon's 10 s
        try:
            os.close(KNOWN_FD)    # slot closed; daemon re-arms to 0600 next
        except OSError:
            pass


if __name__ == "__main__":
    main()
