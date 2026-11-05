#!/usr/bin/env python3
"""Solve BBLS by forcing M to zero through the broken EC addition.

Remote TLS endpoint:
    HOST=bbls.challs.ingeniums.club PORT=9450 TLS=1 python3 solve.py

Local plain-TCP container:
    HOST=127.0.0.1 PORT=13415 TLS=0 python3 solve.py
"""

import json
import os

from pwn import context, remote


HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "13415"))
TLS = os.environ.get("TLS", "0").lower() in {"1", "true", "yes"}

context.log_level = "error"


def request(io, payload):
    io.sendline(json.dumps(payload).encode())
    return json.loads(io.recvline(timeout=10))


io = remote(HOST, PORT, ssl=TLS)
try:
    q = request(io, {"option": "get_Q"})

    # With px == qx, the buggy inverse of dx == 0 becomes zero,
    # making the resulting x-coordinate M equal to zero.
    request(io, {"option": "update_M", "px": q["qx"], "py": 0})

    # (1, 2, 1) is the BN128 generator in the optimized representation.
    result = request(
        io,
        {"option": "check", "gx": 1, "gy": 2, "gz": 1, "hsh": "0"},
    )
    print(result.get("msg", result))
finally:
    io.close()
