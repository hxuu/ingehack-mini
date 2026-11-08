#!/usr/bin/env python3
"""Solve BBLSv2.

Remote:
    python3 solve.py

Local plain TCP:
    HOST=127.0.0.1 PORT=13416 TLS=0 python3 solve.py
"""

import json
import os
import socket
import ssl


HOST = os.environ.get("HOST", "bblsv2.challs.ingeniums.club")
PORT = int(os.environ.get("PORT", "9450"))
TLS = os.environ.get("TLS", "1").lower() in {"1", "true", "yes"}

# BN128 subgroup order. It is smaller than the server's coordinate modulus.
CURVE_ORDER = 21888242871839275222246405745257275088548364400416034343698204186575808495617
FIELD_MODULUS = 21888242871839275222246405745257275088696311157297823662689037894645226208583


def request(io, payload):
    io.sendall(json.dumps(payload).encode() + b"\n")
    data = b""
    while not data.endswith(b"\n"):
        chunk = io.recv(4096)
        if not chunk:
            raise RuntimeError("server closed the connection")
        data += chunk
    return json.loads(data)


raw = socket.create_connection((HOST, PORT), timeout=10)
io = ssl.create_default_context().wrap_socket(raw, server_hostname=HOST) if TLS else raw
try:
    q = request(io, {"option": "get_Q"})
    qx, qy = q["qx"], q["qy"]

    # Choose lambda=1. Then x(P+Q) is exactly CURVE_ORDER:
    # px = 1 - qx - r, py = qy - (qx - px), modulo p.
    px = (1 - qx - CURVE_ORDER) % FIELD_MODULUS
    py = (qy - (qx - px)) % FIELD_MODULUS
    updated = request(io, {"option": "update_M", "px": px, "py": py})
    if updated.get("M") != CURVE_ORDER:
        raise RuntimeError(f"failed to set the subgroup order: {updated}")

    result = request(
        io,
        {"option": "check", "gx": 1, "gy": 2, "gz": 1, "hsh": "0"},
    )
    print(result.get("msg", result))
finally:
    io.close()
