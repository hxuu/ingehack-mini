#!/usr/bin/env bash
# ROLE=entry — sshd plus author-side interaction logging.
#
# The interesting caps come from the service (cap_add: NET_ADMIN on top of the
# Docker default set) so `capsh --print` shows the decoy the players are meant
# to chase.
set -Eeuo pipefail
trap 'rc=$?; echo "entry-start: FAILED (line ${LINENO}, rc=${rc})" >&2' ERR

# --- interaction logging ------------------------------------------------------
# The player's shell hooks append to /var/log/escape/entry.log; a root tail
# mirrors it to the container log so the author can watch `docker logs <entry>`
# live. Per-session bash/psql histories live under sessions/.
printf 'entry' > /run/escape-role
mkdir -p /var/log/escape/sessions
: >> /var/log/escape/entry.log
chmod 1777 /var/log/escape/sessions
chmod 666  /var/log/escape/entry.log
stdbuf -oL tail -F -n +1 /var/log/escape/entry.log 2>/dev/null &

exec /usr/sbin/sshd -D -e
