#!/usr/bin/env python3
"""Solve BBLS by forcing M to zero through the broken EC addition."""

import json
import os
import socket


HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "13415"))


def request(stream, payload):
    stream.write(json.dumps(payload).encode() + b"\n")
    stream.flush()
    return json.loads(stream.readline())


with socket.create_connection((HOST, PORT), timeout=10) as sock:
    with sock.makefile("rwb") as stream:
        q = request(stream, {"option": "get_Q"})

        # With px == qx, the buggy inverse of dx == 0 becomes zero,
        # making the resulting x-coordinate M equal to zero.
        request(stream, {"option": "update_M", "px": q["qx"], "py": 0})

        # (1, 2, 1) is the BN128 generator in the optimized representation.
        result = request(
            stream,
            {"option": "check", "gx": 1, "gy": 2, "gz": 1, "hsh": "0"},
        )
        print(result.get("msg", result))
