#!/usr/bin/env python3
import sys

KEY = 0x37

def encode(data: bytes) -> str:
    return bytes([b ^ KEY for b in data]).hex()

def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <file>")
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        data = f.read()
    with open(sys.argv[1] + ".enc", "w") as f:
        f.write(encode(data))

if __name__ == "__main__":
    main()
