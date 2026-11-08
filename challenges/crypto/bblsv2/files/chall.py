from py_ecc.optimized_bn128 import G1, G2, multiply, pairing, is_on_curve, b, FQ
from hashlib import sha256
import json
import os
import sys

p = 21888242871839275222246405745257275088696311157297823662689037894645226208583
FLAG = os.environ.get(
    "FLAG", "ingehack{???????????????????????????????????????????????????}"
).encode()


def egcd(a, n):
    old_r, r = a % n, n
    old_s, s = 1, 0
    while r > 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
    if old_r != 1:
        raise ValueError("not invertible")
    while old_s < 0:
        old_s += n
    return old_s


def ec_add(P, Q):
    x1, y1 = P
    x2, y2 = Q
    dx = (x2 - x1) % p
    inv = egcd(dx, p)
    lam = ((y2 - y1) * inv) % p
    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)


def to_curve(h, G):
    return multiply(G, h)


class Challenge:

    def __init__(self):
        self.x = int.from_bytes(os.urandom(24), "big")
        self.M = 21
        self.Q = None

    def mint_Q(self):
        self.Q = (
            int.from_bytes(os.urandom(32), "big") % p,
            int.from_bytes(os.urandom(32), "big") % p,
        )
        return self.Q

    def update_M(self, P):
        if self.Q is None:
            self.mint_Q()
        m = ec_add(P, self.Q)[0]
        self.Q = None
        if m == 0:
            raise ValueError("batch coefficient must be non-zero")
        self.M = m
        return self.M

    def bls_verify(self, hsh, G):
        h = int(sha256(FLAG).hexdigest(), 16)
        H = to_curve(h, G2)
        if not is_on_curve(G, b):
            return False
        received_H = to_curve(hsh, G2)
        xH = multiply(H, self.x)
        xG = multiply(G, self.x)
        xMH = multiply(xH, self.M)
        xMG = multiply(xG, self.M)
        l = pairing(xMH, G1)
        r = pairing(received_H, xMG)
        return l == r

    def challenge(self, your_input):
        if "option" not in your_input:
            return {"error": "uhhh you forgot the option `-`"}
        handlers = {
            "get_Q": self._h_get_Q,
            "update_M": self._h_update_M,
            "check": self._h_check,
        }
        handler = handlers.get(your_input["option"])
        if handler is None:
            return {"error": "Invalid option"}
        return handler(your_input)

    def _h_get_Q(self, your_input):
        qx, qy = self.mint_Q()
        return {"msg": "layer 2 partner minted", "qx": qx, "qy": qy}

    def _h_update_M(self, your_input):
        try:
            px = int(your_input["px"])
            py = int(your_input["py"])
            if self.Q is None:
                return {"error": "call get_Q first"}
            m = self.update_M((px, py))
        except Exception as e:
            return {"error": str(e)}
        return {"msg": "layer 2 updated", "M": m}

    def _h_check(self, your_input):
        try:
            gx = int(your_input["gx"])
            gy = int(your_input["gy"])
            gz = int(your_input["gz"])
            G = (FQ(gx), FQ(gy), FQ(gz))
            hsh = int(your_input["hsh"], 16)
            if not (0 <= hsh < p):
                return {"error": "bad hsh"}
            if self.bls_verify(hsh, G):
                return {"msg": FLAG.decode()}
            return {"msg": "arj3 ghdwa!"}
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    chal = Challenge()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            res = chal.challenge(json.loads(line))
        except Exception as e:
            res = {"error": str(e)}
        print(json.dumps(res), flush=True)
