# shellcheck shell=bash
# escape — shared persistent-log-directory helper (sourced by entry-start.sh
# and db-start.sh, both run as root at container start).
#
# The instancer backs the `logs` volume with /var/log/ingehack/escape on the
# challs VM (see chall.yaml). Each instance writes to its own subdirectory,
# named after the per-instance exposed hostname, so teams never share logs.
# Mode 1733: shell users can write their own session files, but cannot list
# the directory or delete files they do not own.

# The per-instance exposed hostname, e.g. escape-abc123.challs.example.
# Falls back to the container hostname for local runs.
__escape_instance_name() {
    local instance

    instance=$(printf '%s' "${RCTF_EXPOSED_HOSTNAMES:-}" \
        | grep -o '"host":"[^"]*"' 2>/dev/null | head -1 | cut -d'"' -f4)
    [ -n "$instance" ] || instance=${HOSTNAME:-local}
    instance=${instance//[^A-Za-z0-9._-]/_}
    printf '%s\n' "$instance"
}

__escape_persist_instance() {
    local root=${ESCAPE_PERSIST_DIR:-/var/log/escape-persist}
    local instance

    [ -d "$root" ] || return 1

    instance=$(__escape_instance_name)
    mkdir -p "$root/$instance" 2>/dev/null || return 1
    chmod 1733 "$root/$instance" 2>/dev/null || true
    printf '%s\n' "$root/$instance"
}
