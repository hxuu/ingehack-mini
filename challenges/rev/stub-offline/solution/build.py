#!/usr/bin/env python3

import base64
import gzip
import hashlib
import hmac
import os
from pathlib import Path
import random
import re
import shlex
import struct
import subprocess
import tempfile
import zlib


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MASK = 0xFFFFFFFF
DELTA = 0x9E3779B9
PART1 = b"l0ck3d_up"
PART2 = b"5p4gh3tt1"
PART3 = b"c0mp1"
PART5 = b"3lfhdr"
PART6 = b"0ffl1n3_r4t3"


def derive(label, length):
    out = b""
    for counter in range((length + 31) // 32):
        out += hashlib.sha256(b"stub-offline/v1/" + label + struct.pack("<I", counter)).digest()
    return out[:length]


def fnv(data, bits):
    value, prime = ((2166136261, 16777619) if bits == 32 else
                    (14695981039346656037, 1099511628211))
    mask = (1 << bits) - 1
    for byte in data:
        value = ((value ^ byte) * prime) & mask
    return value


def xxtea_encrypt(data, key):
    v = list(struct.unpack("<3I", data))
    k = struct.unpack("<4I", key)
    z, total = v[-1], 0
    for _ in range(23):
        total = (total + DELTA) & MASK
        e = (total >> 2) & 3
        for p in range(3):
            y = v[(p + 1) % 3]
            mx = ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)) ^ (
                (total ^ y) + (k[(p & 3) ^ e] ^ z))
            v[p] = (v[p] + mx) & MASK
            z = v[p]
    return struct.pack("<3I", *v)


def rc4(data, key):
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) & 255
        state[i], state[j] = state[j], state[i]
    i = j = 0
    out = bytearray()
    for byte in data:
        i = (i + 1) & 255
        j = (j + state[i]) & 255
        state[i], state[j] = state[j], state[i]
        out.append(byte ^ state[(state[i] + state[j]) & 255])
    return bytes(out)


def xtea_ctr(data, shared, nonce):
    key = (shared, shared ^ 0xA5C31F73, nonce & MASK, nonce >> 32)
    out = bytearray()
    for block in range((len(data) + 7) // 8):
        counter = (nonce + block) & 0xFFFFFFFFFFFFFFFF
        left, right = counter & MASK, counter >> 32
        total = 0
        for _ in range(32):
            left = (left + (((right << 4 ^ right >> 5) + right) ^
                            (total + key[total & 3]))) & MASK
            total = (total + DELTA) & MASK
            right = (right + (((left << 4 ^ left >> 5) + left) ^
                              (total + key[(total >> 11) & 3]))) & MASK
        stream = struct.pack("<2I", left, right)
        out.extend(a ^ b for a, b in zip(data[block * 8:block * 8 + 8], stream))
    return bytes(out)


def matrix_rank(matrix):
    rows = [row[:] for row in matrix]
    rank = 0
    for col in range(len(rows)):
        pivot = next((r for r in range(rank, len(rows)) if rows[r][col]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        inv = pow(rows[rank][col], -1, 257)
        rows[rank] = [v * inv % 257 for v in rows[rank]]
        for r in range(rank + 1, len(rows)):
            factor = rows[r][col]
            rows[r] = [(a - factor * b) % 257 for a, b in zip(rows[r], rows[rank])]
        rank += 1
    return rank


def c_array(data):
    return "{" + ",".join(str(x) for x in data) + "}"


def make_header():
    key1, key3 = derive(b"xxtea", 16), derive(b"rc4", 8)
    cipher1 = xxtea_encrypt(PART1 + b"\x00" * 3, key1)
    cipher3 = rc4(PART3, key3)
    rng = random.Random(derive(b"matrix", 32))
    while True:
        matrix = [[rng.randrange(257) for _ in range(9)] for _ in range(9)]
        if matrix_rank(matrix) == 9:
            break
    target = [sum(a * b for a, b in zip(row, PART2)) % 257 for row in matrix]
    salt = int.from_bytes(derive(b"elf", 8), "little")

    code = bytearray()
    for i, byte in enumerate(PART5):
        mask, rotate, bias = derive(b"vm/" + bytes([i]), 3)
        rotate = 1 + rotate % 7
        x = byte ^ mask
        expected = (((x << rotate) | (x >> (8 - rotate))) + bias) & 255
        code.extend((0x11, i, 0x22, mask, 0x33, rotate, 0x55, bias, 0x44, expected))
    code.append(0xFF)

    p, g = 2147483647, 7
    # Check that 7 has order p-1.
    assert all(pow(g, (p - 1) // q, p) != 1 for q in (2, 3, 7, 11, 31, 151, 331))
    a = 1 + fnv(PART6, 32) % (p - 2)
    b = 1 + int.from_bytes(derive(b"server", 4), "little") % (p - 2)
    client, server = pow(g, a, p), pow(g, b, p)
    shared = pow(server, a, p)
    nonce = int.from_bytes(derive(b"transcript", 8), "little")
    plaintext = PART6 + struct.pack("<I", zlib.crc32(PART6))
    cipher6 = xtea_ctr(plaintext, shared, nonce)

    header = f"""static const struct PACKED {{
    uint8_t magic[8], key[16], cipher[12];
}} stage1 RECORD = {{{c_array(derive(b"record/1", 8))}, {c_array(key1)}, {c_array(cipher1)}}};
static const struct PACKED {{
    uint8_t magic[8]; uint32_t dimension; uint16_t matrix[81], target[9];
}} stage2 RECORD = {{{c_array(derive(b"record/2", 8))}, 9,
    {c_array([v for row in matrix for v in row])}, {c_array(target)}}};
static const struct PACKED {{
    uint8_t magic[8], key[8], cipher[5];
}} stage3 RECORD = {{{c_array(derive(b"record/3", 8))}, {c_array(key3)}, {c_array(cipher3)}}};
static const struct PACKED {{
    uint8_t magic[8]; uint64_t salt;
}} stage4 RECORD = {{{c_array(derive(b"record/4", 8))}, UINT64_C({salt})}};
static const struct PACKED {{
    uint8_t magic[8]; uint32_t size; uint8_t code[{len(code)}];
}} stage5 RECORD = {{{c_array(derive(b"record/5", 8))}, {len(code)}, {c_array(code)}}};
static const struct PACKED {{
    uint8_t magic[8]; uint32_t p, g, client, server; uint64_t nonce; uint8_t cipher[16];
}} stage6 RECORD = {{{c_array(derive(b"record/6", 8))}, {p}, {g}, {client}, {server},
    UINT64_C({nonce}), {c_array(cipher6)}}};
"""
    return header, salt


def main():
    header, salt = make_header()
    compiler = shlex.split(os.environ.get("CC", "gcc"))
    with tempfile.TemporaryDirectory(prefix="stub-offline-build-") as temporary:
        build_dir = Path(temporary)
        (build_dir / "constants.h").write_text(header)
        library = build_dir / "checks.so"
        command = compiler + [
            "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIC", "-march=x86-64",
            "-ffreestanding", "-fno-builtin", "-fno-stack-protector", "-fno-ident",
            "-fvisibility=hidden", "-nostdlib", "-shared",
            "-Wl,-z,defs,-z,noexecstack,--build-id=none,-s",
            "-I", str(build_dir), str(HERE / "checks.c"), "-o", str(library),
        ]
        subprocess.run(command, check=True)
        native = library.read_bytes()
    if native[:5] != b"\x7fELF\x02" or struct.unpack_from("<H", native, 18)[0] != 62:
        raise RuntimeError("build with an x86-64 Linux compiler")

    part4 = struct.pack("<Q", fnv(native[:64], 64) ^ salt).hex().encode("ascii")
    token = PART1 + PART2 + PART3 + part4 + PART5 + PART6
    assert len(token) == 57
    flag = "ingehack{" + token.decode("ascii") + "}"
    assert flag.encode() not in native
    packed = gzip.compress(native, mtime=0)
    key, nonce = derive(b"wrapper-key", 32), derive(b"wrapper-nonce", 16)
    encrypted = bytearray()
    for offset in range(0, len(packed), 32):
        stream = hashlib.sha256(key + nonce + struct.pack("<I", offset // 32)).digest()
        encrypted.extend(a ^ b for a, b in zip(packed[offset:offset + 32], stream))
    tag = hmac.new(key, nonce + encrypted, hashlib.sha256).hexdigest()
    payload = base64.b64encode(encrypted).decode("ascii")
    template = (HERE / "loader.py.in").read_text()
    replacements = {"KEY": repr(key.hex()), "NONCE": repr(nonce.hex()),
                    "TAG": repr(tag), "PAYLOAD": "\n".join(
                        "    " + repr(payload[i:i + 76]) for i in range(0, len(payload), 76))}
    for name, value in replacements.items():
        template = template.replace("@" + name + "@", value)
    files = ROOT / "files"
    files.mkdir(exist_ok=True)
    handout = files / "stub.py"
    handout.write_text(template)
    handout.chmod(0o755)

    manifest_path = ROOT / "chall.yaml"
    manifest, count = re.subn(r"^flag: .*?$", "flag: " + flag,
                              manifest_path.read_text(), flags=re.MULTILINE)
    assert count == 1
    manifest_path.write_text(manifest)
    print(f"wrote {handout} ({handout.stat().st_size} bytes)")
    print(flag)


if __name__ == "__main__":
    main()
