# escape — interactive login-shell hook (installed as
# /etc/profile.d/escape-session.sh). Silent; see escape-log-common.sh.

[[ -n ${BASH_VERSION:-} ]] || return 0
. /usr/local/lib/escape/log.sh
__escape_setup_interactive
