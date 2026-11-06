#!/usr/bin/env python3
"""Decode the nested NVM1 programs and recover the accepted input."""

import argparse
from pathlib import Path
import struct
import subprocess


def recover_flag(binary: bytes) -> str:
    # main passes this embedded program to the interpreter at RVA 0x1200.
    program = binary[0x2140:0x2140 + 0x1D33]

    while True:
        if len(program) < 20 or program[:4] != b"NVM1":
            raise ValueError("invalid NVM1 program")
        code_size, data_size, message_size = struct.unpack_from("<III", program, 8)
        if len(program) != 20 + code_size + data_size + message_size:
            raise ValueError("invalid NVM1 section sizes")
        code = program[20:20 + code_size]
        data = program[20 + code_size:20 + code_size + data_size]

        # PUSH32 key; DECRYPT_CHILD; CALL_CHILD; RETURN.
        if not (len(code) == 8 and code[0] == 0x01
                and code[5:] == b"\x40\x41\xff"):
            break

        key = struct.unpack_from("<I", code, 1)[0]
        seed = program[5]
        program = bytes(
            value ^ ((key + 29 * seed + 13 * index) & 0xFF)
            for index, value in enumerate(data)
        )[::-1]

    instructions = []
    pc = 0
    operand_sizes = {0x01: 4, 0x02: 2, 0x30: 2, 0x31: 4}
    while pc < len(code):
        opcode = code[pc]
        pc += 1
        size = operand_sizes.get(opcode, 0)
        if pc + size > len(code):
            raise ValueError("truncated instruction")
        operand = int.from_bytes(code[pc:pc + size], "little")
        pc += size
        instructions.append((opcode, operand))

    # Each character has paired >= and <= checks against the same constant.
    # Matching that constant maximizes the weighted validation counter.
    flag = bytearray()
    for index in range(len(instructions) - 2):
        input_op, input_index = instructions[index]
        push_op, character = instructions[index + 1]
        compare_op, _ = instructions[index + 2]
        if (input_op, push_op, compare_op) == (0x02, 0x01, 0x24):
            if input_index != len(flag):
                raise ValueError("unexpected character-check order")
            flag.append(character)

    if not flag:
        raise ValueError("no character checks found")
    return flag.decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "binary", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[1] / "files" / "else_if",
    )
    parser.add_argument("--verify", action="store_true",
                        help="run the binary with the recovered flag")
    args = parser.parse_args()
    binary = args.binary.resolve()
    flag = recover_flag(binary.read_bytes())
    print(flag, flush=True)
    if args.verify:
        result = subprocess.run([str(binary), flag], capture_output=True,
                                text=True, timeout=10, check=True)
        if result.stdout != "validation passed\n":
            raise RuntimeError(f"unexpected validation response: {result.stdout!r}")
        print(result.stdout, end="")


if __name__ == "__main__":
    main()
