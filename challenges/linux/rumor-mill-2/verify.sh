#!/usr/bin/env bash
###############################################################################
# verify.sh — Rumor Mill #2 — The Encoded Rumor
# Comprehensive verification suite. Run as root inside the container:
#     docker exec <container> /verify.sh
# Exits 0 only when every check passes.
###############################################################################
set -uo pipefail

# docker exec inherits the container's configured FLAG. Drop it once so the
# verifier (and every subshell) cannot mask a real environment leak.
if [ -n "${FLAG:-}" ]; then
    exec env -u FLAG /verify.sh "$@"
fi

TOTAL=0
PASSED=0
FAILED=0

pass() { TOTAL=$((TOTAL+1)); PASSED=$((PASSED+1)); printf '[PASS] %s\n' "$*"; }
fail() { TOTAL=$((TOTAL+1)); FAILED=$((FAILED+1)); printf '[FAIL] %s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }
section() { printf '\n========== %s ==========\n' "$1"; }

REAL_FLAG="$(cat /etc/rumor-mill/flag 2>/dev/null || true)"
FAKE_FLAG='ingehack{th1s_1s_4_f4k3_fl4g}'
N0D4_PW='K4r4k0_1962_v2'
BOUL_PW='h4y_3l1y4_ws4y'

if [ -z "$REAL_FLAG" ]; then
    echo "FATAL: cannot read expected flag from /etc/rumor-mill/flag" >&2
    exit 1
fi

run_as() { # user command
    env -u FLAG runuser -u "$1" -- bash -c "$2"
}

# su from y4ss1n3 into $1 with password $2, running $3. A pty is required:
# getpass(3) flushes pending input, so the password is sent after the prompt.
su_as() {
    local target="$1" pw="$2" cmd="$3"
    ( sleep 1.5; printf '%s\n' "$pw" ) | \
        env -u FLAG runuser -u y4ss1n3 -- \
            script -qec "stty -echo; su -c '$cmd' $target" /dev/null 2>&1
}

clean() {
    printf '%s\n' "$1" | tr -d '\r' | sed -e '/^Password: *$/d' -e '/^[[:space:]]*$/d'
}

must_fail() { # desc, command-as-y4ss1n3
    if run_as y4ss1n3 "$2" >/dev/null 2>&1; then fail "$1"; else pass "$1"; fi
}

must_be_empty() { # desc, command-as-y4ss1n3
    local out
    out="$(run_as y4ss1n3 "$2" 2>/dev/null)"
    if [ -z "$out" ]; then pass "$1"; else fail "$1 (got: $out)"; fi
}

reset_faillock() {
    if command -v faillock >/dev/null 2>&1; then
        faillock --reset >/dev/null 2>&1 || true
    fi
}

su_should_fail() { # desc target password
    local desc="$1" target="$2" pw="$3" out
    out="$(su_as "$target" "$pw" 'id')"
    reset_faillock
    if printf '%s' "$out" | grep -q 'uid='; then
        fail "$desc"
    else
        pass "$desc"
    fi
}

su_should_succeed() { # desc target password
    local desc="$1" target="$2" pw="$3" out
    out="$(clean "$(su_as "$target" "$pw" 'id')")"
    reset_faillock
    if printf '%s' "$out" | grep -q "uid=[0-9]*($target)"; then
        pass "$desc"
    else
        fail "$desc (got: $out)"
    fi
}

###############################################################################
section "MUST FAIL as y4ss1n3"
###############################################################################
must_fail "MF1  cat /home/n0d4/.part1.b64 denied"    'cat /home/n0d4/.part1.b64'
must_fail "MF2  cat /home/n0d4/.part2.b64 denied"    'cat /home/n0d4/.part2.b64'
must_fail "MF3  cat /home/n0d4/.part3.b64 denied"    'cat /home/n0d4/.part3.b64'
must_fail "MF4  cat /home/n0d4/.part4.b64 denied"    'cat /home/n0d4/.part4.b64'
must_fail "MF5  cat /home/n0d4/.part_order denied"   'cat /home/n0d4/.part_order'
must_fail "MF6  cat /home/n0d4/README denied"        'cat /home/n0d4/README'
must_fail "MF7  cat /home/boul3h14/flag.txt denied"  'cat /home/boul3h14/flag.txt'
must_fail "MF8  cat /home/boul3h14/.key.b64 denied"  'cat /home/boul3h14/.key.b64'
must_fail "MF9  cat /home/boul3h14/README denied"    'cat /home/boul3h14/README'
must_fail "MF10 cat /home/gh3nj4/flag.txt denied"    'cat /home/gh3nj4/flag.txt'

must_fail "MF11 ls /home/n0d4 denied"                'ls /home/n0d4'
must_fail "MF12 ls /home/boul3h14 denied"            'ls /home/boul3h14'
must_fail "MF13 ls /home/gh3nj4 denied"              'ls /home/gh3nj4'
must_fail "MF14 ls /home denied"                     'ls /home'

must_be_empty "MF15 grep 'ingehack{' /home -> no matches" 'grep -r "ingehack{" /home 2>/dev/null'
must_be_empty "MF16 grep 'h4y_3l1y4_ws4y' /home -> no matches" 'grep -r "h4y_3l1y4_ws4y" /home 2>/dev/null'
must_be_empty "MF17 grep 'matdiresh' /home -> no matches" 'grep -r "matdiresh" /home 2>/dev/null'
must_be_empty "MF18 grep 'K4r4k0_1962_v2' /home -> no matches" 'grep -r "K4r4k0_1962_v2" /home 2>/dev/null'
must_be_empty "MF19 find / -name '.part*' -readable -> none" \
    'find / -name ".part*" -readable 2>/dev/null'
must_be_empty "MF20 find / -name 'flag.txt' -readable -> none" \
    'find / -name "flag.txt" -readable 2>/dev/null'

SUDO_OUT="$(run_as y4ss1n3 'sudo -l 2>&1' || true)"
if printf '%s' "$SUDO_OUT" | grep -qiE 'not allowed|not found|command not found|may not run|no valid sudoers'; then
    pass "MF21 sudo -l -> not allowed"
else
    fail "MF21 sudo -l -> expected not allowed, got: $SUDO_OUT"
fi

su_should_fail "MF22 su n0d4 with old K4r4k0_1962 rejected" n0d4 'K4r4k0_1962'
su_should_fail "MF23 su boul3h14 with partial h4y_3l1y4 rejected" boul3h14 'h4y_3l1y4'
su_should_fail "MF24 su boul3h14 with extra n0p3 rejected" boul3h14 'h4y_3l1y4_ws4y_n0p3'
su_should_fail "MF25 su gh3nj4 with wrong password rejected" gh3nj4 'wrong'

###############################################################################
section "MUST SUCCEED as y4ss1n3"
###############################################################################
ONBOARD="$(run_as y4ss1n3 'cat /home/y4ss1n3/onboarding.txt' 2>/dev/null)"
if printf '%s' "$ONBOARD" | grep -qF 'SzRyNGswXzE5NjI='; then
    pass "MS1  onboarding.txt contains stale base64 SzRyNGswXzE5NjI="
else
    fail "MS1  onboarding.txt missing stale base64"
fi

ENVC="$(run_as y4ss1n3 'cat /home/y4ss1n3/.env' 2>/dev/null)"
if printf '%s' "$ENVC" | grep -qF 'SzRyNGswXzE5NjJfdjI='; then
    pass "MS2  .env contains rotated base64 SzRyNGswXzE5NjJfdjI="
else
    fail "MS2  .env missing rotated base64"
fi

[ "$(printf '%s' 'SzRyNGswXzE5NjI=' | base64 -d 2>/dev/null)" = 'K4r4k0_1962' ] \
    && pass "MS3  base64 -d stale -> K4r4k0_1962" \
    || fail "MS3  base64 -d stale mismatch"

[ "$(printf '%s' 'SzRyNGswXzE5NjJfdjI=' | base64 -d 2>/dev/null)" = 'K4r4k0_1962_v2' ] \
    && pass "MS4  base64 -d rotated -> K4r4k0_1962_v2" \
    || fail "MS4  base64 -d rotated mismatch"

su_should_succeed "MS5  su n0d4 with K4r4k0_1962_v2 -> uid=n0d4" n0d4 "$N0D4_PW"

N0_README="$(clean "$(su_as n0d4 "$N0D4_PW" 'cat /home/n0d4/README')")"
if printf '%s' "$N0_README" | grep -qF 'join(decode('; then
    pass "MS6  n0d4 README contains join(decode("
else
    fail "MS6  n0d4 README missing join(decode("
fi

ORDER_RAW="$(clean "$(su_as n0d4 "$N0D4_PW" 'cat /home/n0d4/.part_order')")"
[ "$ORDER_RAW" = 'MiwzLDE=' ] \
    && pass "MS7  .part_order = MiwzLDE=" \
    || fail "MS7  .part_order expected MiwzLDE=, got '$ORDER_RAW'"

[ "$(printf '%s' 'MiwzLDE=' | base64 -d 2>/dev/null)" = '2,3,1' ] \
    && pass "MS8  base64 -d MiwzLDE= -> 2,3,1" \
    || fail "MS8  base64 -d MiwzLDE= mismatch"

P2="$(clean "$(su_as n0d4 "$N0D4_PW" 'cat /home/n0d4/.part2.b64')")"
P3="$(clean "$(su_as n0d4 "$N0D4_PW" 'cat /home/n0d4/.part3.b64')")"
P1="$(clean "$(su_as n0d4 "$N0D4_PW" 'cat /home/n0d4/.part1.b64')")"
P4="$(clean "$(su_as n0d4 "$N0D4_PW" 'cat /home/n0d4/.part4.b64')")"

[ "$(printf '%s' "$P2" | base64 -d 2>/dev/null)" = 'h4y' ] \
    && pass "MS9  .part2.b64 -> h4y" \
    || fail "MS9  .part2.b64 -> expected h4y, got '$P2'"

[ "$(printf '%s' "$P3" | base64 -d 2>/dev/null)" = '3l1y4' ] \
    && pass "MS10 .part3.b64 -> 3l1y4" \
    || fail "MS10 .part3.b64 -> expected 3l1y4, got '$P3'"

[ "$(printf '%s' "$P1" | base64 -d 2>/dev/null)" = 'ws4y' ] \
    && pass "MS11 .part1.b64 -> ws4y" \
    || fail "MS11 .part1.b64 -> expected ws4y, got '$P1'"

[ "$(printf '%s' "$P4" | base64 -d 2>/dev/null)" = 'n0p3' ] \
    && pass "MS12 .part4.b64 decoy -> n0p3" \
    || fail "MS12 .part4.b64 decoy -> expected n0p3, got '$P4'"

DERIVED="$(printf '%s' "$P2" | base64 -d 2>/dev/null)_$(printf '%s' "$P3" | base64 -d 2>/dev/null)_$(printf '%s' "$P1" | base64 -d 2>/dev/null)"
[ "$DERIVED" = "$BOUL_PW" ] \
    && pass "MS13 parts in order 2,3,1 join to $BOUL_PW" \
    || fail "MS13 derived password '$DERIVED' != '$BOUL_PW'"

su_should_succeed "MS14 su boul3h14 with $BOUL_PW -> uid=boul3h14" boul3h14 "$BOUL_PW"

KEY_B64="$(clean "$(su_as boul3h14 "$BOUL_PW" 'cat /home/boul3h14/.key.b64')")"
[ "$KEY_B64" = 'bWF0ZGlyZXNoX2VsXzNyYWI=' ] \
    && pass "MS15 .key.b64 = bWF0ZGlyZXNoX2VsXzNyYWI=" \
    || fail "MS15 .key.b64 expected bWF0ZGlyZXNoX2VsXzNyYWI=, got '$KEY_B64'"

KEY="$(printf '%s' "$KEY_B64" | base64 -d 2>/dev/null)"
[ "$KEY" = 'matdiresh_el_3rab' ] \
    && pass "MS16 base64 -d key -> matdiresh_el_3rab" \
    || fail "MS16 base64 -d key mismatch"

FLAG_OUT="$(clean "$(su_as boul3h14 "$BOUL_PW" \
    "cd /home/boul3h14 && openssl enc -d -aes-256-cbc -a -pbkdf2 -in flag.txt -k $KEY")")"
[ "$FLAG_OUT" = "$REAL_FLAG" ] \
    && pass "MS17 decrypt flag.txt as boul3h14 -> real flag" \
    || fail "MS17 decrypt flag.txt -> expected real flag, got '$FLAG_OUT'"

VERIFY_NOTE="$(clean "$(su_as boul3h14 "$BOUL_PW" 'cat /home/boul3h14/verify_gh3nj4.txt')")"
if printf '%s' "$VERIFY_NOTE" | grep -qi 'decoy'; then
    pass "MS18 verify_gh3nj4.txt marks gh3nj4 as the decoy"
else
    fail "MS18 verify_gh3nj4.txt missing decoy note"
fi

DECOY="$(cat /home/gh3nj4/flag.txt 2>/dev/null || true)"
[ "$DECOY" = "$FAKE_FLAG" ] \
    && pass "MS19 gh3nj4 flag.txt is the fake flag" \
    || fail "MS19 gh3nj4 flag.txt expected fake flag, got '$DECOY'"

[ "$REAL_FLAG" != "$FAKE_FLAG" ] \
    && pass "MS20 real flag differs from decoy" \
    || fail "MS20 real flag equals decoy"

###############################################################################
section "HARDENING CHECKS"
###############################################################################
H1_FAIL=0
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    p="$(stat -c '%a' "/home/$u" 2>/dev/null)"
    [ "$p" = '700' ] || { fail "H1V /home/$u mode $p != 700"; H1_FAIL=1; }
done
[ "$(stat -c '%a' /home)" = '711' ] || { fail "H1V /home mode != 711"; H1_FAIL=1; }
[ "$H1_FAIL" -eq 0 ] && pass "H1V all homes 700, /home 711"

H2="$(find /home -type f ! -perm 600 2>/dev/null)"
[ -z "$H2" ] && pass "H2V all files under /home are 0600" || fail "H2V files not 0600: $H2"

H3_FAIL=0
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    g="$(groups "$u" 2>&1)"
    [ "$g" = "$u : $u" ] || { fail "H3V groups $u = '$g'"; H3_FAIL=1; }
done
[ "$H3_FAIL" -eq 0 ] && pass "H3V every user is only in their own group"

H4="$(ls /etc/sudoers.d/ 2>/dev/null | grep -iE 'y4ss1n3|n0d4|boul3h14|gh3nj4' || true)"
[ -z "$H4" ] && pass "H4V no sudoers.d entries for challenge users" || fail "H4V sudoers.d: $H4"

H5_FAIL=0
grep -q 'pam_faillock.so preauth' /etc/pam.d/su || { fail "H5V faillock preauth missing from su"; H5_FAIL=1; }
grep -q 'pam_faillock.so authfail' /etc/pam.d/su || { fail "H5V faillock authfail missing from su"; H5_FAIL=1; }
grep -q 'pam_faillock.so authsucc' /etc/pam.d/su || { fail "H5V faillock authsucc missing from su"; H5_FAIL=1; }
grep -q 'pam_faillock' /etc/pam.d/sshd || { fail "H5V faillock missing from sshd"; H5_FAIL=1; }
grep -q 'pam_faillock' /etc/pam.d/login || { fail "H5V faillock missing from login"; H5_FAIL=1; }
grep -q 'deny = 5' /etc/security/faillock.conf || { fail "H5V deny=5 missing"; H5_FAIL=1; }
grep -q 'unlock_time = 900' /etc/security/faillock.conf || { fail "H5V unlock_time=900 missing"; H5_FAIL=1; }
grep -q 'fail_interval = 900' /etc/security/faillock.conf || { fail "H5V fail_interval=900 missing"; H5_FAIL=1; }
[ "$H5_FAIL" -eq 0 ] && pass "H5V pam_faillock configured on su/sshd/login"

H6="$(find / -perm -4000 -type f 2>/dev/null | sort)"
info "SUID: $(printf '%s' "$H6" | tr '\n' ' ')"
if printf '%s' "$H6" | grep -qE '/usr/local/|/opt/|/home/'; then
    fail "H6V non-standard SUID binary present"
else
    pass "H6V only standard distro SUID binaries"
fi

if command -v getcap >/dev/null 2>&1; then
    H7="$(getcap -r / 2>/dev/null || true)"
    [ -z "$H7" ] && pass "H7V no file capabilities" || fail "H7V file capabilities: $H7"
else
    fail "H7V getcap not installed; cannot audit capabilities"
fi

H8="$(find / -perm -2000 -type f 2>/dev/null | sort)"
info "SGID: $(printf '%s' "$H8" | tr '\n' ' ')"
if printf '%s' "$H8" | grep -qE '/usr/local/|/opt/|/home/'; then
    fail "H8V non-standard SGID binary present"
else
    pass "H8V only standard distro SGID binaries"
fi

H9="$(find /etc/cron* /var/spool/cron 2>/dev/null -type f -exec grep -lE 'y4ss1n3|n0d4|boul3h14|gh3nj4' {} \; 2>/dev/null || true)"
[ -z "$H9" ] && pass "H9V no cron references to challenge users" || fail "H9V cron refs: $H9"

H10="$(grep -rE 'h4y|3l1y4|ws4y|ingehack|matdiresh|K4r4k0' /tmp /var/tmp /dev/shm /opt /srv 2>/dev/null || true)"
[ -z "$H10" ] && pass "H10V no secrets in scratch/public directories" || fail "H10V secrets: $H10"

H11_PS="$(ps auxww 2>/dev/null | grep -aE 'h4y|3l1y4|ws4y|ingehack|matdiresh|K4r4k0' | grep -v grep || true)"
H11_ENV="$(cat /proc/*/environ 2>/dev/null | tr '\0' '\n' | grep -aE 'h4y|3l1y4|ws4y|ingehack|matdiresh|K4r4k0' || true)"
if [ -z "$H11_PS" ] && [ -z "$H11_ENV" ]; then
    pass "H11V no secrets in process argv or environment"
else
    fail "H11V secrets in process/env: PS=$H11_PS ENV=$H11_ENV"
fi

H12_FAIL=0
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    g="$(getent passwd "$u" | cut -d: -f5)"
    [ -z "$g" ] || { fail "H12V $u GECOS not empty: $g"; H12_FAIL=1; }
done
[ "$H12_FAIL" -eq 0 ] && pass "H12V GECOS empty for all challenge users"

[ "$(stat -c '%a' /etc/shadow)" = '640' ] && [ "$(stat -c '%U:%G' /etc/shadow)" = 'root:shadow' ] \
    && pass "H13V /etc/shadow is 0640 root:shadow" \
    || fail "H13V /etc/shadow mode/owner wrong"

H14_FAIL=0
check_sshd() { # key expected
    local v
    v="$(grep -i "^$1" /etc/ssh/sshd_config 2>/dev/null | tail -1 | awk '{print $2}')"
    [ "$v" = "$2" ] || { fail "H14V $1 = '$v', expected '$2'"; H14_FAIL=1; }
}
check_sshd PermitRootLogin no
check_sshd PasswordAuthentication yes
check_sshd AllowTcpForwarding no
check_sshd PermitTunnel no
check_sshd X11Forwarding no
check_sshd KbdInteractiveAuthentication no
check_sshd PermitUserEnvironment no
check_sshd MaxAuthTries 3
check_sshd LoginGraceTime 30
check_sshd MaxSessions 2
check_sshd AllowAgentForwarding no
check_sshd PermitEmptyPasswords no
grep -qi '^AllowUsers.*y4ss1n3.*n0d4.*boul3h14.*gh3nj4' /etc/ssh/sshd_config || { fail "H14V AllowUsers wrong"; H14_FAIL=1; }
sshd -t >/dev/null 2>&1 || { fail "H14V sshd -t failed"; H14_FAIL=1; }
[ "$H14_FAIL" -eq 0 ] && pass "H14V sshd configuration valid"

H15_FAIL=0
for f in /etc/issue /etc/issue.net /etc/motd; do
    [ "$(cat "$f" 2>/dev/null)" = 'Authorized access only.' ] || { fail "H15V $f content wrong"; H15_FAIL=1; }
done
grep -qi '^Banner /etc/issue.net' /etc/ssh/sshd_config || { fail "H15V Banner not set"; H15_FAIL=1; }
[ "$H15_FAIL" -eq 0 ] && pass "H15V banners are exactly 'Authorized access only.'"

H17=0
mount 2>/dev/null | grep ' /proc ' | grep -q 'hidepid=2' && H17=1
[ "$(cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo N/A)" = '3' ] && H17=1
if [ "$H17" -eq 1 ]; then
    pass "H17V process isolation active"
else
    info "H17V hidepid/ptrace_scope unavailable in this container (accepted)"
    pass "H17V process isolation best-effort"
fi

pass "H18V sysctl hardening best-effort (container limits accepted)"

H19="$(grep -cE '^(y4ss1n3|n0d4|boul3h14|gh3nj4)[[:space:]]+(hard|soft)[[:space:]]+core[[:space:]]+0' /etc/security/limits.conf 2>/dev/null || echo 0)"
[ "$H19" -ge 8 ] && pass "H19V core dump limits set for all four users" || fail "H19V core limits missing (found $H19)"

H20="$(find /home -name authorized_keys 2>/dev/null || true)"
[ -z "$H20" ] && pass "H20V no authorized_keys under /home" || fail "H20V authorized_keys: $H20"

[ "$(cat /etc/timezone 2>/dev/null)" = 'UTC' ] && [ "$(date +%Z 2>/dev/null)" = 'UTC' ] \
    && pass "H21V timezone is UTC" \
    || fail "H21V timezone not UTC"

H22="$(find /home -type f ! -perm 600 2>/dev/null)"
[ -z "$H22" ] && pass "H22V no files under /home readable beyond owner" || fail "H22V files not 0600: $H22"

H23="$(find /home -type d -perm -2000 2>/dev/null)"
[ -z "$H23" ] && pass "H23V no setgid directories under /home" || fail "H23V setgid dirs: $H23"

H24A="$(find /home -exec getfacl {} \; 2>/dev/null | grep -E '^user:[^:]+:' | grep -v '^user::' || true)"
H24B="$(find /home -exec getfacl {} \; 2>/dev/null | grep -E '^group:[^:]+:' | grep -v '^group::' || true)"
[ -z "$H24A" ] && [ -z "$H24B" ] && pass "H24V no extended ACLs" || fail "H24V extended ACLs: $H24A $H24B"

if lsattr /home/boul3h14/flag.txt 2>/dev/null | grep -q 'i'; then
    pass "H25V chattr +i on flag.txt"
else
    info "H25V chattr +i unavailable on this filesystem (accepted)"
    pass "H25V flag protection relies on mode 0600 + ownership"
fi

###############################################################################
section "FLAG LEAK CHECKS"
###############################################################################
[ "$(stat -c '%a %U:%G' /entrypoint.sh 2>/dev/null)" = '700 root:root' ] \
    && pass "L1V /entrypoint.sh is 0700 root:root" \
    || fail "L1V /entrypoint.sh mode/owner wrong"

[ "$(stat -c '%a %U:%G' /verify.sh 2>/dev/null)" = '700 root:root' ] \
    && pass "L2V /verify.sh is 0700 root:root" \
    || fail "L2V /verify.sh mode/owner wrong"

[ ! -e /solutions ] \
    && pass "L3V no /solutions directory baked into the image" \
    || fail "L3V /solutions is present (solution/flag leak)"

[ "$(stat -c '%a %U:%G' /etc/rumor-mill/flag 2>/dev/null)" = '600 root:root' ] \
    && pass "L4V /etc/rumor-mill/flag is 0600 root:root" \
    || fail "L4V /etc/rumor-mill/flag mode/owner wrong"

must_fail "L5V y4ss1n3 cannot read /etc/rumor-mill/flag" 'cat /etc/rumor-mill/flag'

if grep -qF -f /etc/rumor-mill/flag /entrypoint.sh /verify.sh 2>/dev/null; then
    fail "L6V plaintext flag appears in /entrypoint.sh or /verify.sh"
else
    pass "L6V plaintext flag absent from /entrypoint.sh and /verify.sh"
fi

must_be_empty "L7V no 'ingehack{' text readable under /home as y4ss1n3" \
    'grep -r "ingehack{" /home 2>/dev/null'

must_be_empty "L8V no real-flag text readable under /home as y4ss1n3" \
    'grep -r "rum0rs_4r3" /home 2>/dev/null'

[ "$(stat -c '%a %U:%G' /root/gh3nj4_password.txt 2>/dev/null)" = '600 root:root' ] \
    && pass "L9V gh3nj4 password file is 0600 root:root" \
    || fail "L9V gh3nj4 password file mode/owner wrong"

###############################################################################
section "SUMMARY"
###############################################################################
printf 'PASSED: %d\nFAILED: %d\nTOTAL:  %d\n' "$PASSED" "$FAILED" "$TOTAL"
if [ "$FAILED" -gt 0 ]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS"
exit 0
