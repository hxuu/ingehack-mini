#!/usr/bin/env bash
# watchdog.sh — Cutout anti-snooping + liveness guard.
#   * kills any 'cat /proc/*/fd/3' (fd-3 snooping attempt)
#   * in systemd mode: restarts any inactive cutout-Px.service
# (In supervisor mode the supervisor's own respawn loop does the restarts.)
# The kill pattern lives in this FILE, not in argv, so pkill does not
# self-match this script's own command line.
set -u

pkill -f 'cat /proc/[0-9]*/fd/3' 2>/dev/null || true

if [ "$(ps -p 1 -o comm= 2>/dev/null)" = "systemd" ]; then
    for unit in cutout-P1 cutout-P2 cutout-P3 cutout-P4 cutout-P5 cutout-P6 cutout-sshd cutout-keeper; do
        systemctl is-active --quiet "${unit}.service" 2>/dev/null \
            || systemctl restart "${unit}.service" 2>/dev/null \
            || true
    done
fi

exit 0
