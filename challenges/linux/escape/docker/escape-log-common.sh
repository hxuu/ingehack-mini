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
# Everything is written to:
#   /var/log/escape/<role>.log                       (append-only, mirrored to
#                                                     `docker logs` by a root tail)
#   /var/log/escape/sessions/<session>.log           (per-session detail)
#   /var/log/escape/sessions/<session>.history       (bash history, per session)
#   /var/log/escape/sessions/<session>.psql          (psql history, per session)
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
__escape_sid="${__escape_role}-$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null)-$$-${RANDOM:-0}"
__escape_file="${__escape_logdir}/sessions/${__escape_sid}.log"
__escape_busy=0
__escape_prev=

mkdir -p "${__escape_logdir}/sessions" 2>/dev/null || true

# Append one structured line to the central and per-session logs.
__escape_emit() {
    (( __escape_busy )) && return 0
    __escape_busy=1
    local line detail
    detail=${2:-}
    detail=${detail//$'\n'/\\n}
    detail=${detail//$'\r'/}
    line=$(printf '%s | role=%s | session=%s | user=%s | tty=%s | ssh=%s | event=%s | %s' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" \
        "${__escape_role}" "${__escape_sid}" "${USER:-?}" "${SSH_TTY:-${TTY:-?}}" \
        "${SSH_CONNECTION:-local}" "${1:-?}" "${detail}" 2>/dev/null) || line=
    if [[ -n ${line} ]]; then
        printf '%s\n' "${line}" >>"${__escape_central}" 2>/dev/null || true
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
