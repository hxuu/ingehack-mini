#!/usr/bin/env bash
set -e

# Inject flag from environment if provided (ADR 0004), default to placeholder
FLAG_CONTENT="${FLAG:-ingehack{placeholder_flag_replaced_at_deploy}}"
printf '%s\n' "$FLAG_CONTENT" > /flag
chown root:root /flag
chmod 600 /flag

exec /usr/sbin/sshd -D "$@"
