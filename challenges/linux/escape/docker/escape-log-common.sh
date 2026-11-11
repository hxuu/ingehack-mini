# shellcheck shell=bash
# escape — interaction logging library (sourced by the login/exec hooks).
#
# It records what a player runs, per shell session, so the author can review
# interactions after the fact. It is observability, NOT a security boundary:
# a player can always disable it in their own shell.
#
# Used by:
#   /usr/local/bin/escape-shell        — logs `ssh host 'cmd'` invocations
#   /etc/profile.d/escape-session.sh   — interactive login shells
#   /etc/bash.bashrc (appended)        — interactive shells, incl. the db
#                                        reverse shell (`bash -i` as postgres)
#
# Live view (container lifetime):
#   /var/log/escape/<role>.log                       (append-only, mirrored to
#                                                     `docker logs` by a root tail)
#
# Durable view (survives instance deletion):
#   /var/log/escape-persist/<instance>/<session>.log      (per-session detail)
#   /var/log/escape-persist/<instance>/<session>.history  (bash history)
#   /var/log/escape-persist/<instance>/<session>.psql     (psql history)
#
# <instance> is the per-instance exposed hostname (e.g. escape-abc123); the
# host path behind /var/log/escape-persist is /var/log/ingehack/escape on the
# challs VM. entry-start.sh/db-start.sh create the instance directory with
# mode 1733, so shell users can write their own session files but cannot list
# other teams' sessions. Files are mode 0600.
#
# The library must stay silent on stdout/stderr: it is sourced by shells whose
# output may be parsed.

[[ -n ${BASH_VERSION:-} ]] || return 0
[[ -n ${__ESCAPE_LOG_LOADED:-} ]] && return 0
__ESCAPE_LOG_LOADED=1

__escape_role=$(cat /run/escape-role 2>/dev/null) || __escape_role=unknown
__escape_logdir=${ESCAPE_LOG_DIR:-/var/log/escape}
__escape_central=${__escape_logdir}/${__escape_role}.log
__escape_started=$(date -u +%s 2>/dev/null) || __escape_started=0

# Per-instance identity. entry-start.sh/db-start.sh record it in
# /run/escape-instance (readable by every shell, including the PostgreSQL
# reverse shell, whose environment PostgreSQL strips down). Fall back to the
# instancer-substituted hostnames, then the container hostname.
__escape_instance=$(cat /run/escape-instance 2>/dev/null) || __escape_instance=
if [[ -z ${__escape_instance} ]]; then
    __escape_instance=$(printf '%s' "${RCTF_EXPOSED_HOSTNAMES:-}" \
        | grep -o '"host":"[^"]*"' 2>/dev/null | head -1 | cut -d'"' -f4)
fi
[[ -n ${__escape_instance} ]] || __escape_instance=${HOSTNAME:-local}
__escape_instance=${__escape_instance//[^A-Za-z0-9._-]/_}

# Durable per-instance directory. It is created by entry-start.sh/db-start.sh
# (root) before any shell starts; a shell user can write inside it but cannot
# create it. Fall back to the in-container directory for local runs/tests.
__escape_persist_root=${ESCAPE_PERSIST_DIR:-/var/log/escape-persist}
__escape_base="${__escape_logdir}/sessions"
if [[ -n ${__escape_instance} && -d ${__escape_persist_root}/${__escape_instance} \
      && -w ${__escape_persist_root}/${__escape_instance} ]]; then
    __escape_base="${__escape_persist_root}/${__escape_instance}"
    __escape_durable=1
else
    __escape_durable=0
fi

__escape_sid="${__escape_role}-$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null)-$$-$(od -An -N8 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n')"
[[ ${__escape_sid} == *- ]] && __escape_sid="${__escape_sid}${RANDOM:-0}"
__escape_file="${__escape_base}/${__escape_sid}.log"
__escape_busy=0
__escape_prev=

mkdir -p "${__escape_logdir}/sessions" 2>/dev/null || true
[[ ${__escape_durable} -eq 1 ]] || { mkdir -p "${__escape_base}" 2>/dev/null || true; }

# Create a private file without changing the player's umask.
__escape_private_file() {
    local f=$1
    [[ -e ${f} ]] && return 0
    (umask 077; : >>"${f}") 2>/dev/null || true
    chmod 600 "${f}" 2>/dev/null || true
    return 0
}

# Append one structured line to the central and per-session logs.
__escape_emit() {
    (( __escape_busy )) && return 0
    __escape_busy=1
    local line detail
    detail=${2:-}
    detail=${detail//$'\n'/\\n}
    detail=${detail//$'\r'/}
    line=$(printf '%s | instance=%s | role=%s | session=%s | user=%s | tty=%s | ssh=%s | event=%s | %s' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" \
        "${__escape_instance}" "${__escape_role}" "${__escape_sid}" \
        "${USER:-?}" "${SSH_TTY:-${TTY:-?}}" \
        "${SSH_CONNECTION:-local}" "${1:-?}" "${detail}" 2>/dev/null) || line=
    if [[ -n ${line} ]]; then
        printf '%s\n' "${line}" >>"${__escape_central}" 2>/dev/null || true
        __escape_private_file "${__escape_file}"
        printf '%s\n' "${line}" >>"${__escape_file}" 2>/dev/null || true
    fi
    __escape_busy=0
    return 0
}

# PROMPT_COMMAND body: log the command line that just ran.
__escape_prompt() {
    (( __escape_busy )) && return 0
    local h c
    h=$(HISTTIMEFORMAT= builtin history 1 2>/dev/null) || return 0
    [[ -n ${h} ]] || return 0
    [[ ${h} == "${__escape_prev}" ]] && return 0
    __escape_prev=${h}
    # strip leading blanks and the history number
    c=${h#"${h%%[![:space:]]*}"}
    c=${c#* }
    c=${c#"${c%%[![:space:]]*}"}
    [[ -n ${c} ]] || return 0
    __escape_emit cmd "cwd=${PWD:-?} | ${c}"
    return 0
}

__escape_setup_interactive() {
    [[ $- == *i* ]] || return 0
    [[ -n ${__ESCAPE_INTERACTIVE_SETUP:-} ]] && return 0
    __ESCAPE_INTERACTIVE_SETUP=1

    # One history file per session: this also keeps the planted
    # /home/player/.bash_history (the credential leak) from being overwritten.
    export HISTFILE="${__escape_file%.log}.history"
    export HISTSIZE=100000
    export HISTFILESIZE=100000
    export HISTCONTROL=
    export HISTIGNORE=
    export HISTTIMEFORMAT='%F %T '
    export PSQL_HISTORY="${__escape_file%.log}.psql"
    __escape_private_file "${HISTFILE}"
    __escape_private_file "${PSQL_HISTORY}"

    __escape_emit start "mode=interactive | version=bash-${BASH_VERSION} | host=${HOSTNAME:-?} | uid=${EUID:-?}"
    __escape_prev=

    if [[ -n ${PROMPT_COMMAND:-} ]]; then
        PROMPT_COMMAND="__escape_prompt; ${PROMPT_COMMAND}"
    else
        PROMPT_COMMAND="__escape_prompt"
    fi

    trap 'rc=$?; __escape_emit end "duration=$(( $(date -u +%s 2>/dev/null || echo 0) - ${__escape_started:-0} ))s | rc=${rc}"' EXIT
    return 0
}
