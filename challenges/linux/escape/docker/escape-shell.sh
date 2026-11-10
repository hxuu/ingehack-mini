#!/usr/bin/env bash
# escape — login shell wrapper (the player's passwd shell).
#
# sshd starts this for both interactive sessions and `ssh host 'cmd'`. It logs
# the one-off command string before handing off to bash; interactive shells are
# logged by /etc/profile.d/escape-session.sh and /etc/bash.bashrc instead.
#
# Keep this silent and side-effect free: its output is the player's output.

. /usr/local/lib/escape/log.sh

if [[ $# -ge 2 && ${1:-} == "-c" ]]; then
    __escape_emit start "mode=exec | uid=${EUID:-?}"
    __escape_emit exec "cwd=${PWD:-?} | ${2:-}"
    exec /bin/bash "$@"
fi

if [[ $# -eq 0 && -t 0 ]]; then
    # interactive login session: keep /etc/profile + profile.d behaviour
    exec /bin/bash -l
fi

__escape_emit start "mode=exec | uid=${EUID:-?}"
__escape_emit exec "cwd=${PWD:-?} | argv=$*"
exec /bin/bash "$@"
