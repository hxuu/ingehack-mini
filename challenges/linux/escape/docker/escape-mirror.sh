# shellcheck shell=bash
# escape — root-owned mirror of the per-session logs into the durable volume.
#
# The shell hooks (escape-log-common.sh) write per-session .log/.history/.psql
# files inside the container as the shell's own user (player uid 1000, or
# postgres uid 999 for the COPY ... TO PROGRAM reverse shell). Those uids are
# identical in every instance, so pointing the hooks at the shared durable
# volume would let one team read another team's sessions by naming their
# hostname and session file.
#
# Instead the players only ever write into the container's own filesystem,
# and this root watcher copies each new session file into the durable
# directory. Root creates the copies mode 0600, so no unprivileged uid can
# read them, in this instance or any other.
#
# Usage (sourced by entry-start.sh / db-start.sh):
#   __escape_mirror_sessions /var/log/escape-persist/<instance>

__escape_mirror_sessions() {
    local persist=$1
    local src=${ESCAPE_LOG_DIR:-/var/log/escape}/sessions
    local base f

    [ -d "$persist" ] || return 1

    (
        # Session files appear at shell start and grow until the shell exits,
        # so discover new files periodically and follow each one forever.
        while :; do
            for f in "$src"/*; do
                [ -f "$f" ] || continue
                base=${f##*/}
                [ -e "$persist/$base" ] && continue
                (umask 077; : >>"$persist/$base") 2>/dev/null || continue
                chmod 600 "$persist/$base" 2>/dev/null || true
                stdbuf -oL tail -F -c +0 -- "$f" >>"$persist/$base" 2>/dev/null &
            done
            sleep 2
        done
    ) &
}
