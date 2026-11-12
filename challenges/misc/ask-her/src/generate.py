#!/usr/bin/env python3
"""generate.py — build one team's Ask Her evidence set at instance start.

Inputs (baked into the image, under ./template):
  traffic_raw.pcap   captured TLS 1.2 session with a placeholder response
  session.json       {marker, client_random, server_random, master_secret, cipher}
  backup_tool        compiled tool carrying fragment A ("4b32")
  notes_rgba.z       zlib-compressed 1024x1024 RGBA background (decoy QR)
  README_challenge.txt

Outputs (into --out):
  backup_corrupted.zip, memory.raw, traffic.pcap, README_challenge.txt, index.html

Per team we pick fresh fragments B and C (4 hex chars each) and re-encrypt the
TLS application-data record with the team's flag. The master secret itself is
unchanged, so the memory image and the capture stay consistent.

No flag is ever baked into the image: the flag arrives as --flag (from
RCTF_FLAG) and only ever exists inside the encrypted pcap record.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import struct
import subprocess
import sys
import zlib
import zipfile

XOR_KEY = 0x5A
CIPHER_SUITE = 0x002F            # TLS_RSA_WITH_AES_128_CBC_SHA
FRAG_A = "4b32"                  # baked into backup_tool
MEM_SIZE = 16 * 1024 * 1024
OFF_ELF = 0x0000
OFF_DECOY = 0x1000
OFF_MARKER = 0x2000
OFF_SECRET = 0x2008
OFF_CRC = 0x2038
OFF_FRAG_A = 0x2040
OFF_DECOY_A = 0x2050
FLAG_RE = re.compile(r"^ingehack\{[A-Za-z0-9_]+\}$")


def die(msg):
    sys.exit(f"generate: {msg}")


# ------------------------------------------------------------------ obfuscation
def obf(data):
    return bytes(b ^ XOR_KEY for b in data)


def keystream(frag_a, frag_b, frag_c, n=48):
    d = hashlib.sha256((frag_a + frag_b + frag_c).encode()).digest()
    return (d * (n // len(d) + 2))[:n]


# ------------------------------------------------------------------------ PNG
def png_encode(width, height, rgba):
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)                                  # filter: None
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data +
                struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            chunk(b"IEND", b""))


def build_notes(template_dir, frag_c):
    """Patch the team's 2-byte fragment C into the alpha channel."""
    base = zlib.decompress(
        open(os.path.join(template_dir, "notes_rgba.z"), "rb").read())
    rgba = bytearray(base)
    assert len(rgba) == 1024 * 1024 * 4
    b0, b1 = bytes.fromhex(frag_c)          # 2 bytes -> "c0de"-style hex
    rgba[(700 * 1024 + 512) * 4 + 3] = b0 ^ XOR_KEY
    rgba[(700 * 1024 + 513) * 4 + 3] = b1 ^ XOR_KEY
    return png_encode(1024, 1024, bytes(rgba))


# ------------------------------------------------------------------------ ZIP
def build_zip(readme, tool, notes_png, session_dat):
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        z.writestr("backup_tool", tool)
        z.writestr("notes.png", notes_png)
        z.writestr("session.dat", session_dat)
    raw = buf.getvalue()
    eocd = raw.rfind(b"PK\x05\x06")
    if eocd < 0:
        die("zip EOCD not found")
    cd_size, cd_off = struct.unpack("<II", raw[eocd + 12:eocd + 20])
    body = raw[:cd_off]
    rnd = bytearray(secrets.token_bytes(cd_size + 22))
    for sig in (b"PK\x01\x02", b"PK\x05\x06"):
        while sig in rnd:
            rnd[rnd.find(sig):rnd.find(sig) + 4] = secrets.token_bytes(4)
    out = body + bytes(rnd)
    if out.count(b"PK\x03\x04") != 4 or b"PK\x01\x02" in out or b"PK\x05\x06" in out:
        die("corrupted zip shape is wrong")
    return out


# --------------------------------------------------------------------- memory
def build_memory(tool, session, frag_b, frag_c):
    ms = bytes.fromhex(session["master_secret"])
    marker = bytes.fromhex(session["marker"])
    if len(ms) != 48 or len(marker) != 8:
        die("bad session secret/marker")
    mem = bytearray(secrets.token_bytes(MEM_SIZE))
    mem[OFF_ELF:OFF_ELF + 64] = tool[:64]
    mem[OFF_DECOY:OFF_DECOY + 14] = obf(b"decoy_fragment")
    mem[OFF_DECOY + 32:OFF_DECOY + 36] = obf(b"4b33")
    mem[OFF_DECOY + 64:OFF_DECOY + 68] = obf(b"1f33")
    ks = keystream(FRAG_A, frag_b, frag_c, len(ms))
    mem[OFF_MARKER:OFF_MARKER + 8] = marker
    mem[OFF_SECRET:OFF_SECRET + 48] = bytes(a ^ b for a, b in zip(ms, ks))
    mem[OFF_CRC:OFF_CRC + 4] = struct.pack("<I", zlib.crc32(ms) & 0xFFFFFFFF)
    mem[OFF_FRAG_A:OFF_FRAG_A + 4] = obf(FRAG_A.encode())
    mem[OFF_DECOY_A:OFF_DECOY_A + 4] = obf(b"4b33")
    return bytes(mem)


# ----------------------------------------------------------------------- pcap
def parse_pcap(raw):
    if raw[:4] == b"\xd4\xc3\xb2\xa1":
        endian = "<"
    elif raw[:4] == b"\xa1\xb2\xc3\xd4":
        endian = ">"
    else:
        die(f"unknown pcap magic {raw[:4].hex()}")
    linktype = struct.unpack(endian + "I", raw[20:24])[0]
    pkts, off = [], 24
    while off + 16 <= len(raw):
        ts, tus, incl, _orig = struct.unpack(endian + "IIII", raw[off:off + 16])
        pkts.append({"data": raw[off + 16:off + 16 + incl],
                     "ts": ts, "tus": tus})
        off += 16 + incl
    return {"endian": endian, "linktype": linktype, "ghdr": raw[:24],
            "pkts": pkts}


def write_pcap(cap, pkts):
    out = bytearray(cap["ghdr"])
    for p in pkts:
        out += struct.pack(cap["endian"] + "IIII",
                           p["ts"], p["tus"], len(p["data"]), len(p["data"]))
        out += p["data"]
    return bytes(out)


def l3_offset(cap):
    if cap["linktype"] == 1:
        return 14
    if cap["linktype"] == 113:
        return 16
    die(f"unsupported linktype {cap['linktype']}")


def csum(data):
    if len(data) % 2:
        data += b"\x00"
    s = 0
    for i in range(0, len(data), 2):
        s += struct.unpack(">H", data[i:i + 2])[0]
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return (~s) & 0xFFFF


class Pkt:
    def __init__(self, data, l3):
        self.data = data
        self.l3 = l3
        self.ok = False
        if len(data) < l3 + 20:
            return
        if data[l3] >> 4 != 4:
            return
        self.ihl = (data[l3] & 0xF) * 4
        if len(data) < l3 + self.ihl + 20 or data[l3 + 9] != 6:
            return
        self.ip_hdr = bytearray(data[l3:l3 + self.ihl])
        self.tcp_off = l3 + self.ihl
        self.doff = (data[self.tcp_off + 12] >> 4) * 4
        if len(data) < self.tcp_off + self.doff:
            return
        self.tcp_hdr = bytearray(data[self.tcp_off:self.tcp_off + self.doff])
        self.sport, self.dport, self.seq, self.ack = struct.unpack(
            ">HHII", bytes(self.tcp_hdr[:12]))
        self.flags = self.tcp_hdr[13]
        self.payload = bytes(data[self.tcp_off + self.doff:])
        self.ok = True


def rebuild_pkt(base, seq, ack, flags, payload, ts, tus):
    ip = bytearray(base.ip_hdr)
    tcp = bytearray(base.tcp_hdr)
    struct.pack_into(">I", tcp, 4, seq)
    struct.pack_into(">I", tcp, 8, ack)
    tcp[13] = flags
    struct.pack_into(">H", ip, 2, len(ip) + len(tcp) + len(payload))
    ip[10:12] = b"\x00\x00"
    struct.pack_into(">H", ip, 10, csum(bytes(ip)))
    tcp[16:18] = b"\x00\x00"
    pseudo = (bytes(ip[12:16]) + bytes(ip[16:20]) + b"\x00\x06" +
              struct.pack(">H", len(tcp) + len(payload)))
    struct.pack_into(">H", tcp, 16, csum(pseudo + bytes(tcp) + payload))
    return {"data": base.data[:base.l3] + bytes(ip) + bytes(tcp) + payload,
            "ts": ts, "tus": tus}


def tls_records(stream):
    out, off = [], 0
    while off + 5 <= len(stream):
        typ = stream[off]
        ver = stream[off + 1:off + 3]
        ln = struct.unpack(">H", stream[off + 3:off + 5])[0]
        if typ not in (20, 21, 22, 23) or ver not in (b"\x03\x01", b"\x03\x02", b"\x03\x03"):
            break
        if off + 5 + ln > len(stream):
            break
        out.append({"off": off, "type": typ, "body": stream[off + 5:off + 5 + ln]})
        off += 5 + ln
    return out


def prf_sha256(secret, label, seed, n):
    seed = label + seed
    a = hmac.new(secret, seed, hashlib.sha256).digest()
    out = b""
    while len(out) < n:
        out += hmac.new(secret, a + seed, hashlib.sha256).digest()
        a = hmac.new(secret, a, hashlib.sha256).digest()
    return out[:n]


def tls_cbc_record(key, mac_key, seq, ctype, plaintext, iv=None):
    """RFC 7366 Encrypt-then-MAC: IV || ciphertext || MAC(20)."""
    pad = 16 - (len(plaintext) % 16)
    data = plaintext + bytes([pad - 1]) * pad
    if iv is None:
        iv = secrets.token_bytes(16)
    enc = subprocess.run(
        ["openssl", "enc", "-aes-128-cbc", "-nosalt",
         "-K", key.hex(), "-iv", iv.hex()],
        input=data, capture_output=True, check=True).stdout
    fragment = iv + enc
    mac = hmac.new(mac_key,
                   struct.pack(">Q", seq) + bytes([ctype]) +
                   b"\x03\x03" + struct.pack(">H", len(fragment)) + fragment,
                   hashlib.sha1).digest()
    return fragment + mac


def build_pcap(template, session, flag):
    cap = parse_pcap(open(template, "rb").read())
    l3 = l3_offset(cap)
    parsed = []
    for p in cap["pkts"]:
        pk = Pkt(p["data"], l3)
        if pk.ok:
            p["pkt"] = pk
            parsed.append(p)
    if not parsed:
        die("no TCP packets in template")

    port = None
    for p in parsed:
        pk = p["pkt"]
        if pk.payload[:1] == b"\x16" and pk.payload[5:6] == b"\x02":
            port = pk.sport
            break
    if port is None:
        die("no ServerHello in template")

    def stream_of(pred):
        buf, meta = bytearray(), []
        for p in parsed:
            pk = p["pkt"]
            if not pred(pk) or not pk.payload:
                continue
            meta.append({"stream_off": len(buf), "pkt": p})
            buf += pk.payload
        return bytes(buf), meta

    sstream, smeta = stream_of(lambda pk: pk.sport == port)
    srecs = tls_records(sstream)

    seen_ccs, enc_seq, app_start, app_seq = False, 0, None, None
    for r in srecs:
        if r["type"] == 20:
            seen_ccs = True
            continue
        if not seen_ccs:
            continue
        if r["type"] == 23:
            app_start, app_seq = r["off"], enc_seq
            break
        if r["type"] in (22, 21):
            enc_seq += 1
    if app_start is None:
        die("no server application-data record in template")

    ms = bytes.fromhex(session["master_secret"])
    cr = bytes.fromhex(session["client_random"])
    sr = bytes.fromhex(session["server_random"])
    kb = prf_sha256(ms, b"key expansion", sr + cr, 2 * 20 + 2 * 16)
    server_mac, server_key = kb[20:40], kb[56:72]

    body = (f"<html><body><h1>backup vault</h1>"
            f"<p>session recovered</p><pre>{flag}</pre></body></html>").encode()
    http = (b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n"
            b"Connection: close\r\nContent-Length: " +
            str(len(body)).encode() + b"\r\n\r\n" + body)

    holder = None
    for m in sorted(smeta, key=lambda m: m["stream_off"]):
        pl = m["pkt"]["pkt"].payload
        if m["stream_off"] <= app_start < m["stream_off"] + len(pl):
            holder = m
            break
    if holder is None:
        die("could not map application-data record to a packet")
    hp = holder["pkt"]["pkt"]
    prefix_len = app_start - holder["stream_off"]
    seq_at_app = hp.seq + prefix_len
    holder_idx = next(i for i, p in enumerate(parsed) if p is holder["pkt"])
    keep = parsed[:holder_idx]

    rec_body = tls_cbc_record(server_key, server_mac, app_seq, 23, http)
    record = b"\x17\x03\x03" + struct.pack(">H", len(rec_body)) + rec_body

    new_pkts = [{"data": p["data"], "ts": p["ts"], "tus": p["tus"]} for p in keep]
    if prefix_len > 0:
        new_pkts.append(rebuild_pkt(hp, hp.seq, hp.ack, hp.flags,
                                    hp.payload[:prefix_len],
                                    holder["pkt"]["ts"], holder["pkt"]["tus"]))
    new_pkts.append(rebuild_pkt(hp, seq_at_app, hp.ack, 0x18, record,
                                holder["pkt"]["ts"], holder["pkt"]["tus"] + 1))

    last_get = None
    for p in keep:
        if p["pkt"].dport == port and p["pkt"].payload:
            last_get = p
    if last_get is not None:
        cseq = last_get["pkt"].seq + len(last_get["pkt"].payload)
        new_pkts.append(rebuild_pkt(last_get["pkt"], cseq,
                                    seq_at_app + len(record), 0x10, b"",
                                    last_get["ts"], last_get["tus"] + 2))
    return write_pcap(cap, new_pkts)


# ------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flag", required=True)
    ap.add_argument("--out", default="/srv")
    ap.add_argument("--template",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "template"))
    args = ap.parse_args()

    flag = args.flag.strip()
    if not FLAG_RE.match(flag):
        die("RCTF_FLAG is not a valid ingehack{...} flag")

    tdir = args.template
    out = args.out
    os.makedirs(out, exist_ok=True)

    session = json.load(open(os.path.join(tdir, "session.json")))
    tool = open(os.path.join(tdir, "backup_tool"), "rb").read()
    readme = open(os.path.join(tdir, "README_challenge.txt"), "rb").read()

    frag_b = secrets.token_hex(2)          # 4 lowercase hex chars
    frag_c = secrets.token_hex(2)
    if frag_b == FRAG_A:
        frag_b = secrets.token_hex(2)

    notes_png = build_notes(tdir, frag_c)
    session_dat = bytearray(secrets.token_bytes(512))
    session_dat[64:68] = obf(frag_b.encode())

    files = {
        "notes.png": notes_png,
        "session.dat": bytes(session_dat),
    }
    zip_bytes = build_zip(readme, tool, files["notes.png"], files["session.dat"])
    memory = build_memory(tool, session, frag_b, frag_c)
    pcap = build_pcap(os.path.join(tdir, "traffic_raw.pcap"), session, flag)

    open(os.path.join(out, "backup_corrupted.zip"), "wb").write(zip_bytes)
    open(os.path.join(out, "memory.raw"), "wb").write(memory)
    open(os.path.join(out, "traffic.pcap"), "wb").write(pcap)
    open(os.path.join(out, "README_challenge.txt"), "wb").write(readme)
    open(os.path.join(out, "index.html"), "w").write(
        "<!doctype html><meta charset=utf-8><title>Ask Her - evidence</title>"
        "<h1>Evidence drop</h1><ul>" +
        "".join(f'<li><a href="{n}">{n}</a></li>' for n in
                ("backup_corrupted.zip", "memory.raw", "traffic.pcap",
                 "README_challenge.txt")) +
        "</ul><p>This set is unique to your team.</p>")

    print(f"generated evidence in {out}: "
          f"zip={len(zip_bytes)}B mem={len(memory)}B pcap={len(pcap)}B "
          f"(fragments B={frag_b} C={frag_c})")


if __name__ == "__main__":
    main()
