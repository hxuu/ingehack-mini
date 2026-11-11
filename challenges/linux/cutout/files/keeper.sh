#!/usr/bin/env bash
# keeper.sh — spawn one keeper per ledger label, as uid boul3h14.
# Runs forever: rescues any keeper that exits (boot races, stray kills).
set -u
mkdir -p /run/cutout 2>/dev/null || true
chmod 1777 /run/cutout 2>/dev/null || true

declare -A KEEP_PID
labels_from_ledger() { awk '!/^#/ && NF==3 {print $1}' /var/lib/vendor-tool/.ledger; }

while true; do
    for label in $(labels_from_ledger); do
        if [ -n "${KEEP_PID[$label]:-}" ] && kill -0 "${KEEP_PID[$label]}" 2>/dev/null; then
            continue
        fi
        runuser -u boul3h14 -- /usr/bin/python3 /usr/local/bin/keeper.py "$label" &
        KEEP_PID[$label]=$!
    done
    sleep 3
done
