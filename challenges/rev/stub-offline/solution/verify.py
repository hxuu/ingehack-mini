#!/usr/bin/env python3

import argparse
import base64
import ctypes
import hashlib
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    parser = argparse.ArgumentParser(description="Check the build")
    parser.add_argument("--rebuild", action="store_true", help="check the rebuild too")
    args = parser.parse_args()
    handout = ROOT / "files" / "stub.py"
    solver = runpy.run_path(str(HERE / "solve.py"))
    flag = solver["recover"](handout)
    declared = re.search(r"^flag: (.+)$", (ROOT / "chall.yaml").read_text(), re.MULTILINE)
    assert declared is not None and flag == declared[1], "solver/manifest flag mismatch"
    native = solver["extract"](handout)
    assert flag.encode() not in native and flag.encode() not in handout.read_bytes()

    token = flag[9:-1].encode("ascii")
    cuts = (0, 9, 18, 23, 39, 45, 57)
    with tempfile.TemporaryDirectory(prefix="stub-offline-review-") as directory:
        path = Path(directory) / "checks.so"
        path.write_bytes(native)
        library = ctypes.CDLL(str(path))
        for i in range(6):
            check = getattr(library, f"check{i + 1}")
            check.argtypes = (ctypes.c_char_p, ctypes.c_size_t)
            check.restype = ctypes.c_int
            part = token[cuts[i]:cuts[i + 1]]
            assert check(part, len(part)) == 1, f"check{i + 1}: correct input rejected"
            assert check(None, len(part)) == 0
            assert check(part, len(part) - 1) == 0
            assert check(part + b"!", len(part) + 1) == 0
            for position in range(len(part)):
                mutation = bytearray(part)
                mutation[position] ^= 1
                assert check(bytes(mutation), len(part)) == 0, (i + 1, position)
    print("checks 1-6: ok (57 mutations rejected)")
    print("length and null checks: ok")

    # -I -S excludes site packages.
    command = [sys.executable, "-I", "-S", str(handout)]
    for candidate in (flag, token.decode("ascii")):
        result = subprocess.run(command + [candidate], capture_output=True, text=True, timeout=10)
        assert (result.returncode, result.stdout) == (0, flag + "\n"), result
    wrong = ["", flag[:-1], "ingehack{" + "é" * 57 + "}"]
    for index in cuts[:-1]:
        mutation = bytearray(token)
        mutation[index] ^= 1
        wrong.append("ingehack{" + mutation.decode("ascii") + "}")
    wrong.append("ingehack{" + token[:23].decode() + token[23:39].decode().upper()
                 + token[39:].decode() + "}")
    for candidate in wrong:
        result = subprocess.run(command + [candidate], capture_output=True, text=True, timeout=10)
        assert (result.returncode, result.stdout) == (1, "false\n"), result
    usage = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert usage.returncode == 2 and "usage:" in usage.stderr
    print("stub: ok")

    namespace = runpy.run_path(str(handout))
    unpack = namespace["unpack"]
    globals_ = unpack.__globals__
    original = globals_["PAYLOAD"]
    corrupted = bytearray(base64.b64decode(original))
    corrupted[0] ^= 1
    globals_["PAYLOAD"] = base64.b64encode(corrupted).decode("ascii")
    try:
        unpack()
    except ValueError as error:
        assert str(error) == "damaged payload"
    else:
        raise AssertionError("damaged payload was accepted")
    finally:
        globals_["PAYLOAD"] = original
    print("payload tag: ok")

    if args.rebuild:
        paths = (handout, ROOT / "chall.yaml")
        before = [hashlib.sha256(path.read_bytes()).digest() for path in paths]
        subprocess.run([sys.executable, str(HERE / "build.py")], check=True,
                       capture_output=True, text=True, timeout=60)
        after = [hashlib.sha256(path.read_bytes()).digest() for path in paths]
        assert before == after, "rebuild changed the handout or manifest"
        print("rebuild: identical")
    print(flag)


if __name__ == "__main__":
    main()
