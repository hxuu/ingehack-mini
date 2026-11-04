#!/bin/sh
set -eu

# The instancer injects the per-team flag as RCTF_FLAG. The challenge binary
# reads ./flag.txt, so materialise it in the working directory first.
: "${RCTF_FLAG:?RCTF_FLAG is not set}"
printf '%s\n' "$RCTF_FLAG" > /app/flag.txt

exec socat TCP-LISTEN:1337,reuseaddr,fork EXEC:/app/chall,stderr
