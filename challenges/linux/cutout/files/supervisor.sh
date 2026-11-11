#!/usr/bin/env bash
# supervisor.sh — container process farm for Cutout (non-systemd mode, used
# by the instancer where PID 1 is not systemd).
#
# Mirrors the systemd topology 1:1:
#   - one ch41n.py process per ledger label (user ch41n, Restart=always)
#   - keeper.sh spawning 6 keepers as boul3h14 (SCM_RIGHTS fd holding)
#   - watchdog.sh every 30 s (kill fd-3 snoops, restart dead processes)
#   - sshd for the player
set -uo pipefail

LABELS=($(awk '!/^#/ && NF==3 {print $1}' /var/lib/vendor-tool/.ledger))
LOG=/var/log/cutout-supervisor.log

log() { echo "[$(date -u +'%F %T')] $*" >> "$LOG" 2>/dev/null || true; }
spawn() { # spawn <label>
    runuser -u ch41n -- /usr/bin/python3 /home/ch41n/ch41n.py "$1" >/dev/null 2>&1 &
}
all_running() {
    local label
    for label in "${LABELS[@]}"; do
        pgrep -f -- "/home/ch41n/ch41n.py $label" >/dev/null || return 1
    done
    return 0
}

cleanup() {
    for label in "${LABELS[@]}"; do
        pkill -f -- "/home/ch41n/ch41n.py $label" 2>/dev/null
    done
    pgrep -f 'cutout-watchdog' >/dev/null || pkill -f watchdog.sh 2>/dev/null
    exit 0
}
trap cleanup TERM INT

umask 022
mkdir -p /run/cutout
chmod 1777 /run/cutout
touch "$LOG"; chmod 640 "$LOG"; chown root:adm "$LOG" 2>/dev/null || chown root:root "$LOG"

# 1. keeper spawner (as boul3h14 — fd holder fdrules)
/bin/bash /usr/local/bin/keeper.sh &
KEEPER_PID=$!

# 2. six daemons (ch41n) + watcher with per-process respawn semantics
declare -A PIDS
for label in "${LABELS[@]}"; do
    spawn "$label"
done
sleep 1
for label in "${LABELS[@]}"; do
    PIDS[$label]=$(pgrep -f -- "/home/ch41n/ch41n.py $label" | tail -1)
    [ -n "${PIDS[$label]}" ] || log "failed to start $label"
done

# 3. watchdog loop (equivalent of cutout-watchdog.timer, inline)
( while true; do /bin/bash /usr/local/bin/watchdog.sh; sleep 30; done ) &
WATCHDOG_PID=$!

# 4. sshd for the player
/usr/sbin/sshd -D -e &
SSHD_PID=$!
log "supervisor up: keeper=$KEEPER_PID watchdog=$WATCHDOG_PID sshd=$SSHD_PID"

# 5. respawn loop: Restart=always / RestartSec=1 semantics
while true; do
    for label in "${LABELS[@]}"; do
        pgrep -f -- "/home/ch41n/ch41n.py $label" >/dev/null || { log "respawn $label"; spawn "$label"; }
    done
    kill -0 "$KEEPER_PID" 2>/dev/null || { log "respawn keeper"; /bin/bash /usr/local/bin/keeper.sh & KEEPER_PID=$!; }
    kill -0 "$WATCHDOG_PID" 2>/dev/null || { log "respawn watchdog"; ( while true; do /bin/bash /usr/local/bin/watchdog.sh; sleep 30; done ) & WATCHDOG_PID=$!; }
    kill -0 "$SSHD_PID" 2>/dev/null || { log "respawn sshd"; /usr/sbin/sshd -D -e & SSHD_PID=$!; }
    sleep 1
done
