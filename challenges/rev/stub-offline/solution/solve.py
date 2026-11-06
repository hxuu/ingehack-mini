#!/usr/bin/env python3

import argparse
import ast
import base64
import gzip
import hashlib
import hmac
import math
from pathlib import Path
import struct
import subprocess
import sys
import zlib


MASK = 0xFFFFFFFF
DELTA = 0x9E3779B9
TAGS = tuple(bytes.fromhex(value) for value in (
    "2f851c8addd25264", "4b4914702d788acd", "e9da98746c41b0c7",
    "e3a556bf43270aa1", "103b80641211b897", "4d7b7cb5ffc5c87e",
))


def extract(path):
    tree = ast.parse(path.read_text())
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in ("KEY", "NONCE", "TAG", "PAYLOAD"):
                constants[target.id] = ast.literal_eval(node.value)
    key, nonce = bytes.fromhex(constants["KEY"]), bytes.fromhex(constants["NONCE"])
    encrypted = base64.b64decode(constants["PAYLOAD"], validate=True)
    tag = hmac.new(key, nonce + encrypted, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(tag, constants["TAG"]):
        raise ValueError("bad payload tag")
    packed = bytearray()
    for offset in range(0, len(encrypted), 32):
        stream = hashlib.sha256(key + nonce + struct.pack("<I", offset // 32)).digest()
        packed.extend(a ^ b for a, b in zip(encrypted[offset:offset + 32], stream))
    native = gzip.decompress(packed)
    if not native.startswith(b"\x7fELF\x02"):
        raise ValueError("not ELF64")
    return native


def record(native, marker):
    offset = native.find(marker)
    if offset < 0 or native.find(marker, offset + 1) >= 0:
        raise ValueError(f"bad record tag: {marker.hex()}")
    return offset + len(marker)


def xxtea_decrypt(cipher, key):
    v = list(struct.unpack("<3I", cipher))
    k = struct.unpack("<4I", key)
    total, y = (23 * DELTA) & MASK, v[0]
    for _ in range(23):
        e = (total >> 2) & 3
        for p in (2, 1, 0):
            z = v[(p - 1) % 3]
            mx = ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)) ^ (
                (total ^ y) + (k[(p & 3) ^ e] ^ z))
            v[p] = (v[p] - mx) & MASK
            y = v[p]
        total = (total - DELTA) & MASK
    return struct.pack("<3I", *v)


def solve_matrix(native, offset):
    dimension, = struct.unpack_from("<I", native, offset)
    if dimension != 9:
        raise ValueError("bad matrix size")
    values = struct.unpack_from("<90H", native, offset + 4)
    rows = [list(values[9 * i:9 * i + 9]) + [values[81 + i]] for i in range(9)]
    for col in range(9):
        pivot = next(r for r in range(col, 9) if rows[r][col] % 257)
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = pow(rows[col][col], -1, 257)
        rows[col] = [v * scale % 257 for v in rows[col]]
        for r in range(9):
            if r != col:
                factor = rows[r][col]
                rows[r] = [(a - factor * b) % 257 for a, b in zip(rows[r], rows[col])]
    return bytes(row[-1] for row in rows)


def rc4(cipher, key):
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) & 255
        state[i], state[j] = state[j], state[i]
    i = j = 0
    out = bytearray()
    for byte in cipher:
        i = (i + 1) & 255
        j = (j + state[i]) & 255
        state[i], state[j] = state[j], state[i]
        out.append(byte ^ state[(state[i] + state[j]) & 255])
    return bytes(out)


def fnv(data, bits):
    value, prime = ((2166136261, 16777619) if bits == 32 else
                    (14695981039346656037, 1099511628211))
    for byte in data:
        value = ((value ^ byte) * prime) & ((1 << bits) - 1)
    return value


def solve_vm(native, offset):
    size, = struct.unpack_from("<I", native, offset)
    code = native[offset + 4:offset + 4 + size]
    pieces = {}
    pc = 0
    while pc < len(code) and code[pc] != 0xFF:
        if code[pc:pc + 10:2] != bytes((0x11, 0x22, 0x33, 0x55, 0x44)):
            raise ValueError("unknown bytecode")
        index, mask, rotate, bias, expected = code[pc + 1:pc + 10:2]
        value = (expected - bias) & 255
        value = ((value >> rotate) | (value << (8 - rotate))) & 255
        pieces[index] = value ^ mask
        pc += 10
    if pc != len(code) - 1 or code[pc] != 0xFF or sorted(pieces) != list(range(6)):
        raise ValueError("bad bytecode")
    return bytes(pieces[i] for i in range(6))


def discrete_log(g, public, p):
    # Baby-step giant-step.
    width = math.isqrt(p - 1) + 1
    table = {}
    value = 1
    for j in range(width):
        table.setdefault(value, j)
        value = value * g % p
    step = pow(pow(g, width, p), -1, p)
    value = public
    for i in range(width + 1):
        if value in table:
            exponent = i * width + table[value]
            if exponent < p - 1 and pow(g, exponent, p) == public:
                return exponent
        value = value * step % p
    raise ValueError("no discrete logarithm found")


def decrypt_transcript(native, offset):
    p, g, client, server, nonce = struct.unpack_from("<4IQ", native, offset)
    exponent = discrete_log(g, client, p)
    shared = pow(server, exponent, p)
    key = (shared, shared ^ 0xA5C31F73, nonce & MASK, nonce >> 32)
    cipher = native[offset + 24:offset + 40]
    plaintext = bytearray()
    for block in range(2):
        counter = (nonce + block) & 0xFFFFFFFFFFFFFFFF
        left, right, total = counter & MASK, counter >> 32, 0
        for _ in range(32):
            left = (left + (((right << 4 ^ right >> 5) + right) ^
                            (total + key[total & 3]))) & MASK
            total = (total + DELTA) & MASK
            right = (right + (((left << 4 ^ left >> 5) + left) ^
                              (total + key[(total >> 11) & 3]))) & MASK
        stream = struct.pack("<2I", left, right)
        plaintext.extend(a ^ b for a, b in zip(cipher[block * 8:block * 8 + 8], stream))
    piece = bytes(plaintext[:12])
    if len(plaintext) != 16 or zlib.crc32(piece) != struct.unpack_from("<I", plaintext, 12)[0]:
        raise ValueError("transcript CRC mismatch")
    if 1 + fnv(piece, 32) % (p - 2) != exponent:
        raise ValueError("wrong client exponent")
    return piece


def recover(path):
    native = extract(path)
    offset = record(native, TAGS[0])
    padded = xxtea_decrypt(native[offset + 16:offset + 28], native[offset:offset + 16])
    if padded[9:] != b"\x00" * 3:
        raise ValueError("invalid XXTEA padding")
    parts = [padded[:9], solve_matrix(native, record(native, TAGS[1]))]
    offset = record(native, TAGS[2])
    parts.append(rc4(native[offset + 8:offset + 13], native[offset:offset + 8]))
    salt, = struct.unpack_from("<Q", native, record(native, TAGS[3]))
    parts.append(struct.pack("<Q", fnv(native[:64], 64) ^ salt).hex().encode("ascii"))
    parts.append(solve_vm(native, record(native, TAGS[4])))
    parts.append(decrypt_transcript(native, record(native, TAGS[5])))
    if tuple(map(len, parts)) != (9, 9, 5, 16, 6, 12):
        raise ValueError("bad chunk lengths")
    return "ingehack{" + b"".join(parts).decode("ascii") + "}"


def main():
    parser = argparse.ArgumentParser(description="Solve stub.py")
    parser.add_argument("handout", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[1] / "files" / "stub.py")
    parser.add_argument("--verify", action="store_true", help="execute the handout with the flag")
    args = parser.parse_args()
    flag = recover(args.handout)
    print(flag, flush=True)
    if args.verify:
        result = subprocess.run([sys.executable, str(args.handout), flag],
                                capture_output=True, text=True, timeout=10, check=True)
        if result.stdout != flag + "\n":
            raise RuntimeError(f"unexpected validation response: {result.stdout!r}")
        print("ok")


if __name__ == "__main__":
    main()
