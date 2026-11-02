#!/bin/sh
# Runs as the unprivileged app user (uid 10001). The root filesystem is
# read-only, so /flag.txt is a symlink baked into the image that points at
# /tmp/flag.txt, and /tmp is a writable tmpfs. The flag value arrives only via
# the FLAG environment variable; we write it to the file, then remove the
# variable from the environment before exec'ing gunicorn.
set -eu

# deploy-static.sh injects the real flag via FLAG. Fall back to the non-secret
# placeholder so the image also starts locally without the variable.
# Use an explicit test: ${FLAG:-ingehack{undeployed}} would stop the expansion
# at the first "}" and append a stray brace to the value.
if [ -z "${FLAG:-}" ]; then
  FLAG='ingehack{undeployed}'
fi

umask 022
printf '%s\n' "$FLAG" > /tmp/flag.txt
chmod 0644 /tmp/flag.txt

unset FLAG

exec "$@"
