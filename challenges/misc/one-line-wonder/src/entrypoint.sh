#!/bin/sh
set -eu

if [ -n "${FLAG:-}" ]; then
    FLAG_CONTENT="$FLAG"
else
    FLAG_CONTENT='ingehack{placeholder_flag_replaced_at_deploy}'
fi
printf '%s\n' "$FLAG_CONTENT" > /flag.txt
printf '%s\n' 'ingehack{0ld_fl4g_d0nt_subm1t}' > /flag_old.txt
chmod 644 /flag.txt /flag_old.txt

exec socat TCP-LISTEN:1337,reuseaddr,fork \
    EXEC:"timeout 60 python3 -u /app/jail.py",stderr
