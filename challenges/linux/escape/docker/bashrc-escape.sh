# escape — system-wide interactive-shell hook (appended to /etc/bash.bashrc).
# This is what catches the `bash -i` reverse shell on the db container.
# Silent; see escape-log-common.sh.

[[ -n ${BASH_VERSION:-} ]] || return 0
. /usr/local/lib/escape/log.sh
__escape_setup_interactive
