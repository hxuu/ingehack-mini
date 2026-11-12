#!/bin/sh
# Build one team's evidence set, then serve it over HTTP for that instance.
set -eu

if [ -z "${RCTF_FLAG:-}" ]; then
    echo "ask-her: RCTF_FLAG is not set" >&2
    exit 1
fi

# Assign first, then match: writing ${RCTF_FLAG:-ingehack{...}} inline makes
# the shell close the expansion at the first '}' (see docs/status.md).
flag="$RCTF_FLAG"
if ! printf '%s' "$flag" | grep -Eq '^ingehack\{[A-Za-z0-9_]+\}$'; then
    echo "ask-her: RCTF_FLAG is not a valid ingehack{...} flag" >&2
    exit 1
fi

rm -rf /srv/*
mkdir -p /srv

python3 /opt/ask-her/generate.py --flag "$flag" --out /srv

cd /srv
exec python3 -m http.server 5000 --bind 0.0.0.0
