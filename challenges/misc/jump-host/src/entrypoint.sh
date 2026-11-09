#!/bin/bash
set -e

if [ -n "${FLAG:-}" ]; then
    FLAG_CONTENT="$FLAG"
else
    FLAG_CONTENT='ingehack{placeholder_flag_replaced_at_deploy}'
fi
printf '%s\n' "$FLAG_CONTENT" > /home/admin/flag.txt
chown admin:admin /home/admin/flag.txt
chmod 600 /home/admin/flag.txt

ssh-keygen -A
exec /usr/sbin/sshd -D "$@"
