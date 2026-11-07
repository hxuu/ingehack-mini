#!/bin/sh
# Starts as ROOT only long enough to write the flag file root-owned, then
# drops to uid 10001 before exec'ing gunicorn. The app user (and therefore any
# injected command) can read /flag.txt but cannot delete, rename or overwrite
# it: the file is root-owned and /tmp has the sticky bit.
set -eu

[ "$(id -u)" = 0 ] || { echo "entrypoint must start as root" >&2; exit 1; }

# deploy-static.sh injects the real flag via FLAG. Fall back to the non-secret
# placeholder so the image also starts locally without the variable.
if [ -z "${FLAG:-}" ]; then
  FLAG='ingehack{undeployed}'
fi

umask 022
rm -f /tmp/flag.txt            # restarts keep /tmp in production; start clean
printf '%s\n' "$FLAG" > /tmp/flag.txt
chmod 0444 /tmp/flag.txt

unset FLAG                     # gunicorn is exec'd without FLAG in its env

exec setpriv --reuid=10001 --regid=10001 --clear-groups "$@"