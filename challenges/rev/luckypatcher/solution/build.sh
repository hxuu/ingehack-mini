#!/usr/bin/env bash
# Author-side rebuild for luckypatcher. Not shipped to players.
#
#   ./solution/build.sh
#
# Produces files/luckypatcher: x86-64, statically linked, not stripped.
# Reads the flag from chall.yaml; do not duplicate it here.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 solution/gen_flag.py chall.yaml solution/flag_data.h

mkdir -p files
gcc -O0 -g -static -no-pie -fno-stack-protector -fno-inline \
    -o files/luckypatcher solution/luckypatcher.c
chmod +x files/luckypatcher

echo
file files/luckypatcher
echo
nm -n files/luckypatcher | grep -E ' (gate_[0-9]+|print_flag|main)$' || true
