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
# mirrors it to the container log (live, `docker logs <entry>`) and to the
# per-instance durable directory (host /var/log/ingehack/escape/<instance>),
# which survives instance deletion. Per-session files are written inside the
# container and mirrored there by a root watcher, so their durable copies are
# root-owned and unreadable by another instance's player.
printf 'entry' > /run/escape-role
mkdir -p /var/log/escape/sessions
: >> /var/log/escape/entry.log
chmod 1777 /var/log/escape/sessions
chmod 666  /var/log/escape/entry.log

. /usr/local/lib/escape/persist.sh
INSTANCE=$(__escape_instance_name)
printf '%s\n' "$INSTANCE" > /run/escape-instance
chmod 644 /run/escape-instance

PERSIST_DIR=$(__escape_persist_instance) || PERSIST_DIR=
if [ -n "$PERSIST_DIR" ]; then
    : >> "$PERSIST_DIR/entry.log"
    chmod 600 "$PERSIST_DIR/entry.log" 2>/dev/null || true
    stdbuf -oL tail -F -n +1 /var/log/escape/entry.log 2>/dev/null \
        | stdbuf -oL tee -a "$PERSIST_DIR/entry.log" &
    . /usr/local/lib/escape/mirror.sh
    __escape_mirror_sessions "$PERSIST_DIR"
else
    stdbuf -oL tail -F -n +1 /var/log/escape/entry.log 2>/dev/null &
fi

exec /usr/sbin/sshd -D -e
