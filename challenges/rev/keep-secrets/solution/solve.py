#!/usr/bin/env python3
"""Decompile the handout with jadx, recover the key, and decrypt the vault."""
from __future__ import annotations

import base64
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = Path(__file__).resolve().parent
DEFAULT_APK = HERE.parent / "files" / "keep-secrets.apk"


def decompile_class(apk: Path, class_name: str) -> str:
    out = Path(tempfile.mkdtemp(prefix="keepsecrets-jadx-")) / "Class.java"
    subprocess.run(
        [
            "jadx",
            "--no-res",
            "--single-class",
            class_name,
            "--single-class-output",
            str(out),
            str(apk),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return out.read_text(errors="ignore")


def decompile(apk: Path) -> str:
    return "\n".join(
        [
            decompile_class(apk, "com.ingehack.keepsecrets.VaultCrypto"),
            decompile_class(apk, "com.ingehack.keepsecrets.SecretData"),
        ]
    )


def find_passphrase(java: str) -> str:
    match = re.search(r'PASSPHRASE\s*=\s*"([^"]+)"', java)
    if match:
        return match.group(1)

    first = re.search(r'FIRST\s*=\s*"([^"]+)"', java)
    second = re.search(r'SECOND\s*=\s*"([^"]+)"', java)
    if first and second:
        return f"{first.group(1)} {second.group(1)}"

    for candidate in re.findall(r'"([^"\n]*Lelouch[^"\n]*)"', java):
        if "hail" in candidate.lower():
            return candidate

    raise SystemExit("could not recover the passphrase from the decompiled APK")


def main() -> None:
    apk = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_APK
    if not apk.is_file():
        raise SystemExit(f"APK not found: {apk}")

    java = decompile(apk)
    passphrase = find_passphrase(java)
    key = hashlib.sha256(passphrase.encode()).digest()
    print(f"passphrase: {passphrase!r}")
    print(f"key (SHA-256): {key.hex()}")

    def decrypt(blob: str) -> str:
        raw = base64.b64decode(blob, validate=True)
        return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode()

    found = False
    entries = re.findall(
        r'VaultEntry\("([^"]+)",\s*"([A-Za-z0-9+/=]{20,})"\)', java
    )
    if entries:
        for title, blob in entries:
            try:
                plaintext = decrypt(blob)
            except Exception:
                continue
            print(f"{title}: {plaintext}")
            if plaintext.startswith("ingehack{"):
                found = True
    else:
        for blob in sorted(set(re.findall(r'"([A-Za-z0-9+/]{40,}={0,2})"', java))):
            try:
                plaintext = decrypt(blob)
            except Exception:
                continue
            print(plaintext)
            if plaintext.startswith("ingehack{"):
                found = True

    if not found:
        raise SystemExit("no flag found")


if __name__ == "__main__":
    main()
