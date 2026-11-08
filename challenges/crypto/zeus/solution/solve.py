#!/usr/bin/env python3
"""Solve Zeus.

Remote:
    python3 solve.py

Local plain TCP:
    HOST=127.0.0.1 PORT=13417 TLS=0 python3 solve.py
"""

import json
import os
import socket
import ssl


HOST = os.environ.get("HOST", "zeus.challs.ingeniums.club")
PORT = int(os.environ.get("PORT", "9450"))
TLS = os.environ.get("TLS", "1").lower() in {"1", "true", "yes"}

A = 5003
RC0, RC1 = 5, 9
M00, M01, M10, M11 = 2, 1, 1, 3


def request(io, payload):
    io.sendall(json.dumps(payload).encode() + b"\n")
    data = b""
    while not data.endswith(b"\n"):
        chunk = io.recv(4096)
        if not chunk:
            raise RuntimeError("server closed the connection")
        data += chunk
    return json.loads(data)


def alternate_quotient(d):
    q, c = divmod(d, A)
    if q < 2:
        raise RuntimeError(f"this session has no alternate positive quotient for D={d}")
    return q - 1, c + A


raw = socket.create_connection((HOST, PORT), timeout=10)
io = ssl.create_default_context().wrap_socket(raw, server_hostname=HOST) if TLS else raw
try:
    ident = request(io, {"option": "get_id"})
    d0 = (ident["s0"] + RC0) ** 2
    d1 = (ident["s1"] + RC1) ** 2
    q0, c0 = divmod(d0, A)
    q1, c1 = divmod(d1, A)

    # The verifier checks D=A*Q+C but forgets to require C<A. Move one
    # quotient down in either row, adding A to its remainder.
    if q0 >= 2:
        q0, c0 = q0 - 1, c0 + A
    elif q1 >= 2:
        q1, c1 = q1 - 1, c1 + A
    else:
        raise RuntimeError("this random session has no alternate digest")

    out0 = M00 * c0 + M01 * c1
    out1 = M10 * c0 + M11 * c1
    result = request(
        io,
        {
            "option": "submit",
            "Q0": q0,
            "C0": c0,
            "Q1": q1,
            "C1": c1,
            "out0": out0,
            "out1": out1,
        },
    )
    print(result.get("msg", result))
finally:
    io.close()
