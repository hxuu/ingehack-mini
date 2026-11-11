#!/usr/bin/env bash
# entrypoint.sh — Cutout container entrypoint.
#   * supervisor mode (instancer default: PID 1 is not systemd):
#       run the full topology from supervisor.sh (6 daemons + handoff + sshd
#       + watchdog), mirroring the systemd units 1:1.
#
#   systemd mode: used only for local verification — run the image with
#   --entrypoint /lib/systemd/systemd so systemd is PID 1; the enabled
#   cutout-* units then start at boot. Nothing to do here.
set -euo pipefail

if [ "$(ps -p 1 -o comm= 2>/dev/null)" = "systemd" ]; then
    # systemd is PID 1 (local verification runs); a oneshot bootstrap keeps
    # /run/cutout alive inside tmpfs.
    mkdir -p /run/cutout && chmod 755 /run/cutout
    exec sleep infinity
fi

exec /usr/local/bin/supervisor.sh
