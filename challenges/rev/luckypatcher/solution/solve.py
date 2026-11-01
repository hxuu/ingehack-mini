#!/usr/bin/env python3
"""Patch luckypatcher so Alice walks the good path.

Each gate_1..gate_10 function contains one `jne` that jumps to the dead end
because the volatile `alice_step` value is 0 while the gate expects 1..10.
Flipping that `jne` to `je` makes the jump not taken, so execution falls
through into the good branch, prints the scene, and folds the gate key into
`progress`. All ten are required: print_flag only decodes the flag for the
final progress value.

Usage:
    python3 solution/solve.py files/luckypatcher /tmp/luckypatcher.patched
    chmod +x /tmp/luckypatcher.patched
    /tmp/luckypatcher.patched
"""
import os
import re
import subprocess
import sys


def text_section(binary: str) -> tuple[int, int]:
    """Return (VMA, file offset) of .text from objdump -h -w."""
    out = subprocess.check_output(["objdump", "-h", "-w", binary], text=True)
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 6 and parts[1] == ".text":
            return int(parts[3], 16), int(parts[5], 16)
    raise SystemExit("could not find .text in objdump -h output")


def gate_jumps(binary: str) -> dict[str, list[tuple[int, bytes, str]]]:
    """Map gate_N -> [(address, instruction bytes, asm)] for its jumps."""
    out = subprocess.check_output(
        ["objdump", "-d", "-M", "intel", binary], text=True
    )
    gates: dict[str, list[tuple[int, bytes, str]]] = {}
    current = None

    for line in out.splitlines():
        label = re.match(r"^[0-9a-f]+ <(gate_\d+)>:$", line.strip())
        if label:
            current = label.group(1)
            gates[current] = []
            continue
        if not line.strip():
            current = None
            continue
        if current is None:
            continue

        insn = re.match(
            r"^\s*([0-9a-f]+):\s+([0-9a-f ]+?)\s{2,}([a-z].*)$", line
        )
        if not insn:
            continue

        addr = int(insn.group(1), 16)
        raw = bytes.fromhex(insn.group(2))
        asm = insn.group(3)
        if asm.startswith(("jne", "je", "jz", "jnz")):
            gates[current].append((addr, raw, asm))

    return gates


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: solve.py <binary> [output]")
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) == 3 else src + ".patched"

    data = bytearray(open(src, "rb").read())
    text_vma, text_off = text_section(src)
    gates = gate_jumps(src)

    patched = 0
    for name in sorted(gates, key=lambda s: int(s.split("_")[1])):
        jumps = gates[name]
        if not jumps:
            raise SystemExit(f"{name}: no conditional jump found")

        addr, raw, asm = jumps[0]
        file_off = addr - text_vma + text_off

        if len(raw) == 2 and raw[0] == 0x75:  # short jne -> je
            data[file_off] = 0x74
            print(f"{name}: {addr:#x}  jne -> je  ({raw.hex()} -> 74{raw[1]:02x})")
        elif len(raw) == 6 and raw[0] == 0x0F and raw[1] == 0x85:  # near jne -> je
            data[file_off + 1] = 0x84
            print(f"{name}: {addr:#x}  jne near -> je near")
        else:
            raise SystemExit(f"{name}: unexpected jump {raw.hex()} ({asm})")
        patched += 1

    if patched != 10:
        raise SystemExit(f"expected 10 gates, patched {patched}")

    with open(dst, "wb") as f:
        f.write(data)
    os.chmod(dst, 0o755)
    print(f"patched {patched} gates -> {dst}")


if __name__ == "__main__":
    main()
