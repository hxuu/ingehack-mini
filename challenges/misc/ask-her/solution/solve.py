#!/usr/bin/env python3
"""solution.py — reference solver for *Ask Her* (player workflow).

Only the four public artifacts are used:
  backup_corrupted.zip, memory.raw, traffic.pcap, README_challenge.txt

Steps: recover the ZIP entries from the surviving local headers, run the
backup tool (decoy vs. real fragment A), read fragment B from session.dat,
read fragment C from the PNG alpha channel, rebuild/verify the master secret
from memory.raw, then decrypt the TLS application-data record and print the
flag.
"""
import hashlib
import hmac
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
PUBLIC = os.path.join(BASE, "files")

XOR_KEY = 0x5A


def deobf(b):
    return bytes(x ^ XOR_KEY for x in b)


def keystream(a, b, c, n=48):
    d = hashlib.sha256((a + b + c).encode()).digest()
    return (d * (n // len(d) + 2))[:n]


# ---------------------------------------------------- local-header ZIP reader
def read_local_zip(raw):
    entries, off = {}, 0
    while True:
        i = raw.find(b"PK\x03\x04", off)
        if i < 0:
            break
        (_ver, _flags, method, _t, _d, _crc, csize, _usize,
         nlen, elen) = struct.unpack("<HHHHHIIIHH", raw[i + 4:i + 30])
        name = raw[i + 30:i + 30 + nlen].decode("utf-8", "replace")
        start = i + 30 + nlen + elen
        data = raw[start:start + csize]
        if method == 8:
            data = zlib.decompress(data, -15)
        elif method != 0:
            raise SystemExit(f"unsupported compression {method} for {name}")
        entries[name] = data
        off = start + csize
    return entries


# ------------------------------------------------------------- pcap parsing
def png_alpha_pixels(raw, coords):
    """Decode an 8-bit RGBA PNG and return the alpha values at coords."""
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    off, idat = 8, bytearray()
    w = h = depth = ctype = interlace = None
    while off + 8 <= len(raw):
        ln = struct.unpack(">I", raw[off:off + 4])[0]
        typ = raw[off + 4:off + 8]
        data = raw[off + 8:off + 8 + ln]
        off += 12 + ln
        if typ == b"IHDR":
            w, h, depth, ctype, _comp, _filt, interlace = struct.unpack(
                ">IIBBBBB", data)
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
    assert (depth, ctype, interlace) == (8, 6, 0), \
        (depth, ctype, interlace)
    bpp, stride = 4, w * 4
    dec = zlib.decompress(bytes(idat))
    prev, rows, p = bytearray(stride), {}, 0
    for y in range(h):
        f = dec[p]
        p += 1
        line = bytearray(dec[p:p + stride])
        p += stride
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif f != 0:
            raise SystemExit(f"unsupported PNG filter {f}")
        rows[y] = line
        prev = line
    return [rows[y][x * 4 + 3] for x, y in coords]


def parse_pcap(path):
    raw = open(path, "rb").read()
    endian = "<" if raw[:4] == b"\xd4\xc3\xb2\xa1" else ">"
    linktype = struct.unpack(endian + "I", raw[20:24])[0]
    l3 = 14 if linktype == 1 else 16
    pkts, off = [], 24
    while off + 16 <= len(raw):
        ts, tus, incl, orig = struct.unpack(endian + "IIII", raw[off:off + 16])
        data = raw[off + 16:off + 16 + incl]
        off += 16 + incl
        if len(data) < l3 + 20 or data[l3] >> 4 != 4 or data[l3 + 9] != 6:
            continue
        ihl = (data[l3] & 0xF) * 4
        to = l3 + ihl
        doff = (data[to + 12] >> 4) * 4
        sport, dport, seq, ack = struct.unpack(">HHII", data[to:to + 12])
        payload = data[to + doff:]
        pkts.append({"sport": sport, "dport": dport, "seq": seq,
                     "ack": ack, "payload": payload})
    return pkts


def tls_records(stream):
    out, off = [], 0
    while off + 5 <= len(stream):
        t = stream[off]
        ln = struct.unpack(">H", stream[off + 3:off + 5])[0]
        if t not in (20, 21, 22, 23) or off + 5 + ln > len(stream):
            break
        out.append({"type": t, "body": stream[off + 5:off + 5 + ln]})
        off += 5 + ln
    return out


def tls_prf(secret, label, seed, n):
    """TLS 1.2 P_SHA256 (A(i) chain, not raw HMAC of label+seed)."""
    seed = label + seed
    a = hmac.new(secret, seed, hashlib.sha256).digest()
    out = b""
    while len(out) < n:
        out += hmac.new(secret, a + seed, hashlib.sha256).digest()
        a = hmac.new(secret, a, hashlib.sha256).digest()
    return out[:n]


def decrypt_session(pcap_path, master_secret):
    pkts = parse_pcap(pcap_path)
    server_port = None
    for p in pkts:
        if p["payload"][:1] == b"\x16" and p["payload"][5:6] == b"\x02":
            server_port = p["sport"]
            break
    if server_port is None:
        raise SystemExit("no ServerHello in pcap")
    client = [p for p in pkts if p["dport"] == server_port]
    server = [p for p in pkts if p["sport"] == server_port]

    cbuf = bytearray()
    for p in client:
        cbuf += p["payload"]
    sbuf = bytearray()
    for p in server:
        sbuf += p["payload"]

    ch = next(r for r in tls_records(bytes(cbuf))
              if r["type"] == 22 and r["body"][:1] == b"\x01")
    sh = next(r for r in tls_records(bytes(sbuf))
              if r["type"] == 22 and r["body"][:1] == b"\x02")
    client_random = ch["body"][6:38]
    server_random = sh["body"][6:38]

    seen_ccs, seq, app = False, 0, None
    for r in tls_records(bytes(sbuf)):
        if r["type"] == 20:
            seen_ccs = True
            continue
        if not seen_ccs:
            continue
        if r["type"] == 23:
            app = (r["body"], seq)
            break
        if r["type"] in (22, 21):
            seq += 1
    if app is None:
        raise SystemExit("no application-data record")

    kb = tls_prf(master_secret, b"key expansion", server_random + client_random,
                 2 * 20 + 2 * 16)
    server_mac, server_key = kb[20:40], kb[56:72]
    body, app_seq = app
    # RFC 7366 Encrypt-then-MAC: record body = IV || ciphertext || MAC(20)
    fragment, mac = body[:-20], body[-20:]
    exp = hmac.new(server_mac,
                   struct.pack(">Q", app_seq) + b"\x17\x03\x03" +
                   struct.pack(">H", len(fragment)) + fragment,
                   hashlib.sha1).digest()
    if mac != exp:
        raise SystemExit("MAC mismatch (wrong master secret?)")
    iv, enc = fragment[:16], fragment[16:]
    dec = subprocess.run(["openssl", "enc", "-d", "-aes-128-cbc", "-nosalt",
                          "-K", server_key.hex(), "-iv", iv.hex()],
                         input=enc, capture_output=True, check=True).stdout
    pad = dec[-1] + 1
    plaintext = dec[:-pad]
    return plaintext, client_random


def main():
    tmp = tempfile.mkdtemp(prefix="askher-")
    try:
        # 1. recover the archive entries despite the destroyed central dir
        raw = open(os.path.join(PUBLIC, "backup_corrupted.zip"), "rb").read()
        entries = read_local_zip(raw)
        for need in ("backup_tool", "session.dat", "notes.png"):
            if need not in entries:
                raise SystemExit(f"could not recover {need} from archive")
        print(f"[*] recovered {len(entries)} entries from the corrupted zip")

        tool = os.path.join(tmp, "backup_tool")
        open(tool, "wb").write(entries["backup_tool"])
        os.chmod(tool, 0o755)

        # 2. fragment A: decoy vs real (env var)
        env = dict(os.environ)
        env.pop("BACKUP_KEY_A", None)
        decoy = subprocess.run([tool, "--keygen"], capture_output=True,
                               text=True, env=env).stdout.strip()
        env["BACKUP_KEY_A"] = "1"
        real = subprocess.run([tool, "--keygen"], capture_output=True,
                              text=True, env=env).stdout.strip()
        key_a = real.split()[-1]
        print(f"[*] keygen: {decoy!r} without env, {real!r} with BACKUP_KEY_A")
        if key_a != "4b32":
            raise SystemExit("unexpected real fragment A")

        # 3. fragment C: PNG alpha channel (dependency-free PNG decode)
        alphas = png_alpha_pixels(entries["notes.png"], [(512, 700), (513, 700)])
        key_c = bytes(a ^ XOR_KEY for a in alphas).hex()
        print(f"[*] PNG alpha fragments -> {key_c}")

        # 4. fragment B: scan session.dat for a de-XORed hex token
        session = entries["session.dat"]
        cands = []
        for off in range(0, min(256, len(session)) - 3):
            d = deobf(session[off:off + 4])
            try:
                s = d.decode()
            except UnicodeDecodeError:
                continue
            if all(ch in "0123456789abcdef" for ch in s):
                cands.append(s)
        print(f"[*] session.dat candidates: {cands}")

        # 5. locate the marker in memory.raw via the pcap client random
        cap = parse_pcap(os.path.join(PUBLIC, "traffic.pcap"))
        server_port = next(p["sport"] for p in cap
                           if p["payload"][:1] == b"\x16" and
                           p["payload"][5:6] == b"\x02")
        cbuf = bytearray()
        for p in cap:
            if p["dport"] == server_port:
                cbuf += p["payload"]
        ch = next(r for r in tls_records(bytes(cbuf))
                  if r["type"] == 22 and r["body"][:1] == b"\x01")
        client_random = ch["body"][6:38]
        marker = client_random[:8]

        mem = open(os.path.join(PUBLIC, "memory.raw"), "rb").read()
        idx = mem.find(marker)
        if idx < 0:
            raise SystemExit("client-random marker not found in memory.raw")
        print(f"[*] marker found at offset {idx:#x}")
        enc = mem[idx + 8:idx + 56]
        crc = struct.unpack("<I", mem[idx + 56:idx + 60])[0]

        # 6. try B candidates until the CRC32 of the master secret matches
        ms = None
        for key_b in cands:
            trial = bytes(x ^ y for x, y in
                          zip(enc, keystream(key_a, key_b, key_c)))
            if (zlib.crc32(trial) & 0xFFFFFFFF) == crc:
                ms, used_b = trial, key_b
                break
        if ms is None:
            raise SystemExit("could not recover a valid master secret")
        print(f"[*] fragments A={key_a} B={used_b} C={key_c}; "
              f"master secret recovered (CRC32 ok)")

        # 7. decrypt the TLS app-data record
        plaintext, _ = decrypt_session(os.path.join(PUBLIC, "traffic.pcap"), ms)
        body = plaintext.decode("latin-1")
        m = re.search(r"ingehack\{[^}]+\}", body)
        if not m:
            raise SystemExit("flag not found in decrypted HTTP body")
        print(m.group(0))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
