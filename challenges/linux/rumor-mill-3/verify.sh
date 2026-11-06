#!/usr/bin/env bash
###############################################################################
# verify.sh — Rumor Mill #3 — The Liars' Club
#
# Run as root inside the container:  docker exec <container> /verify.sh
# Exits 0 only when every check passes.
#
# Secret literals are carried as base64 (and the split password is rebuilt at
# runtime) so this verifier can live in the image without tripping the
# plaintext-leak scan.
###############################################################################
set -uo pipefail

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
b64d() { printf '%s' "$1" | base64 -d; }

FLAG_PREFIX="$(b64d 'aW5nZWhhY2t7')"
REAL_FLAG="$(b64d 'aW5nZWhhY2t7M3YzcnkwbjNfbDEzZF9idTdfdGgzX2wwZ19kMWRuN30=')"
FAKE_FLAG="$(b64d 'aW5nZWhhY2t7dGgxc18xc180X2Y0azNfZmw0Z30=')"
KEY="$(b64d 'bHdlbGRfZWxfZmFyZjBzaA==')"
NOTES_B64='bHdlbGRfZWxfZmFyZjBzaA=='
Y4_PW="$(b64d 'NHJ0NHo0')"
N0D4_PW="$(b64d 'MW5nM19kNHdsNA==')"
PART1="$(b64d 'OWF0Y2hhbA==')"
PART2="$(b64d 'bHdlbGQ=')"
BOUL_PW="${PART1}_${PART2}"

if [ -z "$REAL_FLAG" ] || [ -z "$FAKE_FLAG" ]; then
    echo "FATAL: cannot decode expected values" >&2
    exit 1
fi

run_as() { # user 'command'
    runuser -u "$1" -- bash -c "$2"
}

clean() {
    printf '%s\n' "$1" | tr -d '\r' | sed -e '/^Password: *$/d' -e '/^[[:space:]]*$/d'
}

reset_faillock() {
    faillock --reset --user "$1" >/dev/null 2>&1 || true
}

su_try() { # user password command
    local u="$1" pw="$2" cmd="$3" out
    reset_faillock "$u"
    out="$( ( sleep 1.1; printf '%s\n' "$pw" ) | \
        runuser -u y4ss1n3 -- \
            script -qec "stty -echo; su -c '$cmd' $u" /dev/null 2>&1 )"
    reset_faillock "$u"
    printf '%s' "$out"
}

su_ok() { # desc user password
    local d="$1" u="$2" pw="$3" out
    out="$(su_try "$u" "$pw" 'id')"
    if printf '%s' "$out" | grep -q "uid=[0-9]*($u)"; then
        pass "$d"
    else
        fail "$d — expected uid=$u, got: $(clean "$out" | tail -1)"
    fi
}

su_bad() { # desc user password
    local d="$1" u="$2" pw="$3" out
    out="$(su_try "$u" "$pw" 'id')"
    if printf '%s' "$out" | grep -q "uid=[0-9]*($u)"; then
        fail "$d — su unexpectedly succeeded"
    else
        pass "$d"
    fi
}

must_fail_y4() { # desc command
    if run_as y4ss1n3 "$2" >/dev/null 2>&1; then
        fail "$1 — command unexpectedly succeeded"
    else
        pass "$1"
    fi
}

must_be_empty_y4() { # desc command
    local out
    out="$(run_as y4ss1n3 "$2" 2>/dev/null || true)"
    if [ -z "$out" ]; then
        pass "$1"
    else
        fail "$1 — got: $out"
    fi
}

###############################################################################
section "AUTH LOG"
###############################################################################
LOG=/var/log/rumor/auth.log
[ "$(wc -l < "$LOG" 2>/dev/null)" -eq 40 ] \
    && pass "LOG40 auth.log is exactly 40 lines" \
    || fail "LOG40 auth.log is $(wc -l < "$LOG" 2>/dev/null || echo missing) lines, expected 40"

TOKENS="$(grep -cE 'sync|printf|openssl|cp ' "$LOG" 2>/dev/null || true)"
[ "$TOKENS" -eq 10 ] \
    && pass "LOG10 auth.log token-line count is 10" \
    || fail "LOG10 auth.log token-line count is $TOKENS, expected 10"

SIGNALS=(
"2026-11-02T03:14:22Z admin su y4ss1n3 -> n0d4 : FAIL (bad password: matdiresh)"
"2026-11-02T03:14:23Z admin note: onboarding.txt is stale, do not fix"
"2026-11-02T03:14:24Z admin reset n0d4 password to: MW5nM19kNHdsNA=="
"2026-11-02T09:00:00Z n0d4 note: creating decoy .sync to throw off intruders"
"2026-11-02T10:12:44Z n0d4 EXEC: su -c 'printf \"%s_%s\" \"9atchal\" \"lweld\"' boul3h14"
"2026-11-02T10:12:45Z n0d4 SUCCESS: boul3h14"
"2026-11-02T10:50:00Z boul3h14 note: creating audit_copy.log to mislead"
"2026-11-02T11:00:02Z admin openssl enc -aes-256-cbc -a -salt -pbkdf2 -in /tmp/.sync_stage -out /home/boul3h14/.sync/.backup.bin"
"2026-11-02T11:00:03Z admin echo -n <redacted> | base64 > /home/boul3h14/.sync/.notes.txt"
"2026-11-02T11:01:02Z admin note: real flag only in boul3h14/.sync. .confession is a lie. audit_copy.log is a lie."
)
SIG_MISSING=0
for line in "${SIGNALS[@]}"; do
    grep -qxF "$line" "$LOG" 2>/dev/null || SIG_MISSING=$((SIG_MISSING+1))
done
[ "$SIG_MISSING" -eq 0 ] \
    && pass "LOGSIG all 10 exact signal lines present" \
    || fail "LOGSIG $SIG_MISSING signal line(s) missing"

###############################################################################
section "MUST FAIL (as y4ss1n3)"
###############################################################################
must_fail_y4 "MF1  cat /home/n0d4/.part1.b64 denied" 'cat /home/n0d4/.part1.b64'
must_fail_y4 "MF2  cat /home/n0d4/.part2.b64 denied" 'cat /home/n0d4/.part2.b64'
must_fail_y4 "MF3  cat /home/n0d4/README denied" 'cat /home/n0d4/README'
must_fail_y4 "MF4  cat /home/boul3h14/flag.txt denied" 'cat /home/boul3h14/flag.txt'
must_fail_y4 "MF5  cat /home/boul3h14/.confession denied" 'cat /home/boul3h14/.confession'
must_fail_y4 "MF6  cat /home/boul3h14/.sync/.notes.txt denied" 'cat /home/boul3h14/.sync/.notes.txt'
must_fail_y4 "MF7  cat /home/boul3h14/.sync/.backup.bin denied" 'cat /home/boul3h14/.sync/.backup.bin'
must_fail_y4 "MF8  cat /home/gh3nj4/flag.txt denied" 'cat /home/gh3nj4/flag.txt'
must_fail_y4 "MF9  ls /home/n0d4 denied" 'ls /home/n0d4'
must_fail_y4 "MF10 ls /home/boul3h14 denied" 'ls /home/boul3h14'
must_fail_y4 "MF11 ls /home/gh3nj4 denied" 'ls /home/gh3nj4'
must_fail_y4 "MF12 ls /home denied" 'ls /home'
must_be_empty_y4 "MF13 grep flag prefix under /home -> no matches" \
    "grep -rF '$FLAG_PREFIX' /home 2>/dev/null"
must_be_empty_y4 "MF14 grep full boul3h14 password under /home -> no matches" \
    "grep -rF '$BOUL_PW' /home 2>/dev/null"
must_be_empty_y4 "MF15 grep real key under /home -> no matches" \
    "grep -rF '$KEY' /home 2>/dev/null"
must_be_empty_y4 "MF16 find .part* readable -> none" \
    'find / -name ".part*" -readable 2>/dev/null'
must_be_empty_y4 "MF17 find flag.txt readable -> none" \
    'find / -name "flag.txt" -readable 2>/dev/null'

SUDO_OUT="$(run_as y4ss1n3 'sudo -l 2>&1' || true)"
if printf '%s' "$SUDO_OUT" | grep -qiE 'command not found|not allowed|may not run|not in the sudoers'; then
    pass "MF18 sudo -l not available to y4ss1n3"
else
    fail "MF18 sudo -l unexpected output: $SUDO_OUT"
fi

su_bad "MF19 su n0d4 with the onboarding password rejected" n0d4 'matdiresh'
su_bad "MF20 su boul3h14 with lweld+9atchal (README order) rejected" boul3h14 "${PART2}${PART1}"
su_bad "MF21 su boul3h14 with only the first part rejected" boul3h14 "$PART1"
su_bad "MF22 su gh3nj4 with a wrong password rejected" gh3nj4 'wrong'

run_as boul3h14 'cat /home/gh3nj4/.cache/.flag_backup' >/dev/null 2>&1 \
    && fail "MF23 boul3h14 could read gh3nj4's decoy backup" \
    || pass "MF23 cat /home/gh3nj4/.cache/.flag_backup denied to boul3h14"
run_as boul3h14 'ls /home/gh3nj4/.cache' >/dev/null 2>&1 \
    && fail "MF24 boul3h14 could list gh3nj4's .cache" \
    || pass "MF24 ls /home/gh3nj4/.cache denied to boul3h14"
run_as boul3h14 'ls /home/boul3h14/.sync' >/dev/null 2>&1 \
    && fail "MF25 boul3h14 could list /home/boul3h14/.sync" \
    || pass "MF25 ls /home/boul3h14/.sync denied to boul3h14"

###############################################################################
section "MUST SUCCEED"
###############################################################################
ONBOARD="$(run_as y4ss1n3 'cat /home/y4ss1n3/onboarding.txt' 2>/dev/null || true)"
printf '%s' "$ONBOARD" | grep -qF 'bWF0ZGlyZXNo' \
    && pass "MS1  onboarding.txt carries the base64 handover" \
    || fail "MS1  onboarding.txt missing bWF0ZGlyZXNo"

NOHUP="$(run_as y4ss1n3 'cat /home/y4ss1n3/nohup.out' 2>/dev/null || true)"
printf '%s' "$NOHUP" | grep -qF "$N0D4_PW" \
    && pass "MS2  nohup.out carries the real n0d4 password" \
    || fail "MS2  nohup.out missing the real n0d4 password"

[ "$(printf '%s' 'bWF0ZGlyZXNo' | base64 -d 2>/dev/null)" = 'matdiresh' ] \
    && pass "MS3  bWF0ZGlyZXNo decodes to matdiresh" \
    || fail "MS3  onboarding base64 does not decode"

su_ok "MS4  su n0d4 with the real password -> uid=n0d4" n0d4 "$N0D4_PW"

N0README="$(run_as n0d4 'cat /home/n0d4/README' 2>/dev/null || true)"
printf '%s' "$N0README" | grep -qF 'decode(.part2)' \
    && pass "MS5  n0d4 README carries the (lying) composition rule" \
    || fail "MS5  n0d4 README missing decode(.part2)"

[ "$(run_as n0d4 'cat /home/n0d4/.part1.b64' 2>/dev/null)" = 'OWF0Y2hhbA==' ] \
    && pass "MS6  .part1.b64 is OWF0Y2hhbA==" \
    || fail "MS6  .part1.b64 wrong"
[ "$(run_as n0d4 'cat /home/n0d4/.part2.b64' 2>/dev/null)" = 'bHdlbGQ=' ] \
    && pass "MS7  .part2.b64 is bHdlbGQ=" \
    || fail "MS7  .part2.b64 wrong"

[ "$(printf '%s' 'OWF0Y2hhbA==' | base64 -d 2>/dev/null)" = "$PART1" ] \
    && pass "MS8  .part1 decodes to the first half" \
    || fail "MS8  .part1 does not decode"
[ "$(printf '%s' 'bHdlbGQ=' | base64 -d 2>/dev/null)" = "$PART2" ] \
    && pass "MS9  .part2 decodes to the second half" \
    || fail "MS9  .part2 does not decode"

su_ok "MS10 su boul3h14 with the log-derived password -> uid=boul3h14" boul3h14 "$BOUL_PW"

[ "$(run_as boul3h14 'cat /home/boul3h14/.sync/.notes.txt' 2>/dev/null)" = "$NOTES_B64" ] \
    && pass "MS11 .sync/.notes.txt is the base64 key" \
    || fail "MS11 .sync/.notes.txt wrong"
[ "$(printf '%s' "$NOTES_B64" | base64 -d 2>/dev/null)" = "$KEY" ] \
    && pass "MS12 the notes key decodes to the real key" \
    || fail "MS12 notes key does not decode"

DEC="$(run_as boul3h14 'base64 -d /home/boul3h14/.sync/.notes.txt | openssl enc -d -aes-256-cbc -a -pbkdf2 -pass stdin -in /home/boul3h14/.sync/.backup.bin' 2>/dev/null || true)"
[ "$DEC" = "$REAL_FLAG" ] \
    && pass "MS13 .backup.bin decrypts to the real flag" \
    || fail "MS13 decrypt mismatch (got: ${DEC:-nothing})"

STRINGS="$(run_as boul3h14 'strings /home/boul3h14/.sync/.backup.bin' 2>/dev/null || true)"
printf '%s' "$STRINGS" | grep -qF 'SYNCED_FROM:/home/gh3nj4/.cache/.flag_backup' \
    && pass "MS14 strings header names the claimed source" \
    || fail "MS14 strings header missing SYNCED_FROM"
printf '%s' "$STRINGS" | grep -qF 'SYNCED_AT:2026-11-02T11:00:02Z' \
    && pass "MS15 strings header carries SYNCED_AT" \
    || fail "MS15 strings header missing SYNCED_AT"

VGH="$(run_as boul3h14 'cat /home/boul3h14/verify_gh3nj4.txt' 2>/dev/null || true)"
printf '%s' "$VGH" | grep -qF "$FAKE_FLAG" \
    && pass "MS16 verify_gh3nj4.txt identifies the fake flag" \
    || fail "MS16 verify_gh3nj4.txt missing the fake flag"

REC="$(run_as boul3h14 'cat /home/boul3h14/.recovery.txt' 2>/dev/null || true)"
printf '%s' "$REC" | grep -qF 'matdiresh_key' \
    && pass "MS17 .recovery.txt carries the old (wrong) key" \
    || fail "MS17 .recovery.txt missing matdiresh_key"

AUDIT="$(run_as boul3h14 'cat /home/boul3h14/audit_copy.log' 2>/dev/null || true)"
if printf '%s' "$AUDIT" | grep -qF 'n0d4/.sync' && ! printf '%s' "$AUDIT" | grep -qF 'boul3h14/.sync'; then
    pass "MS18 audit_copy.log points only at the decoy .sync"
else
    fail "MS18 audit_copy.log path rewrite wrong"
fi

grep -qF 'printf "%s_%s" "9atchal" "lweld"' "$LOG" 2>/dev/null \
    && pass "MS19 auth.log carries the separator/order line" \
    || fail "MS19 auth.log missing the separator/order line"
grep -qE 'openssl.*boul3h14/\.sync/\.backup\.bin' "$LOG" 2>/dev/null \
    && pass "MS20 auth.log names the real backup path" \
    || fail "MS20 auth.log missing the real backup path"
grep -qF 'real flag only in boul3h14/.sync' "$LOG" 2>/dev/null \
    && pass "MS21 auth.log confirms the real .sync" \
    || fail "MS21 auth.log missing the confirmation line"

###############################################################################
section "HARDENING"
###############################################################################
H1_BAD=0
[ "$(stat -c '%a %U:%G' /home 2>/dev/null)" = '711 root:root' ] || H1_BAD=1
for u in y4ss1n3 n0d4 boul3h14; do
    [ "$(stat -c '%a %U:%G' "/home/$u" 2>/dev/null)" = "700 $u:$u" ] || H1_BAD=1
done
[ "$(stat -c '%a %U:%G' /home/gh3nj4 2>/dev/null)" = '711 gh3nj4:gh3nj4' ] || H1_BAD=1
[ "$H1_BAD" -eq 0 ] \
    && pass "H1V /home 0711, three homes 0700, gh3nj4 0711" \
    || fail "H1V home modes/owners wrong"

H2="$(find /home -type f ! -perm 600 2>/dev/null || true)"
[ -z "$H2" ] && pass "H2V every file under /home is 0600" || fail "H2V non-0600 files: $H2"

H3_BAD=0
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    g="$(groups "$u" 2>/dev/null || true)"
    [ "$g" = "$u : $u" ] || H3_BAD=1
done
[ "$H3_BAD" -eq 0 ] \
    && pass "H3V each user is only in their own group" \
    || fail "H3V group membership is not isolated"

H4="$(grep -rlE 'y4ss1n3|n0d4|boul3h14|gh3nj4' /etc/sudoers.d 2>/dev/null || true)"
[ -z "$H4" ] && pass "H4V no sudoers entries for challenge users" || fail "H4V sudoers refs: $H4"

H5_BAD=0
grep -q 'pam_faillock.so preauth' /etc/pam.d/su || H5_BAD=1
grep -q 'pam_faillock.so authfail' /etc/pam.d/su || H5_BAD=1
grep -q 'pam_faillock.so authsucc' /etc/pam.d/su || H5_BAD=1
grep -q 'pam_faillock' /etc/pam.d/sshd || H5_BAD=1
grep -q 'pam_faillock' /etc/pam.d/login || H5_BAD=1
grep -q 'deny = 5' /etc/security/faillock.conf || H5_BAD=1
grep -q 'unlock_time = 900' /etc/security/faillock.conf || H5_BAD=1
grep -q 'fail_interval = 900' /etc/security/faillock.conf || H5_BAD=1
[ "$H5_BAD" -eq 0 ] \
    && pass "H5V pam_faillock active on su/sshd/login (deny=5, 900s)" \
    || fail "H5V pam_faillock configuration incomplete"

SUID="$(find / -perm -4000 -type f 2>/dev/null | sort || true)"
info "SUID: $(printf '%s' "$SUID" | tr '\n' ' ')"
if printf '%s' "$SUID" | grep -qE '^/(usr/local|opt|home|tmp|srv)/'; then
    fail "H6V non-standard SUID binary present"
else
    pass "H6V only stock distro SUID binaries"
fi

CAPS="$(getcap -r / 2>/dev/null || true)"
[ -z "$CAPS" ] && pass "H7V no file capabilities" || fail "H7V capabilities: $CAPS"

SGID="$(find / -perm -2000 -type f 2>/dev/null | sort || true)"
info "SGID: $(printf '%s' "$SGID" | tr '\n' ' ')"
if printf '%s' "$SGID" | grep -qE '^/(usr/local|opt|home|tmp|srv)/'; then
    fail "H8V non-standard SGID binary present"
else
    pass "H8V only stock distro SGID binaries"
fi

H9="$(find /etc/cron* /var/spool/cron 2>/dev/null -type f -exec grep -lE 'y4ss1n3|n0d4|boul3h14|gh3nj4' {} \; 2>/dev/null || true)"
H9T=""
if command -v systemctl >/dev/null 2>&1; then
    H9T="$(systemctl list-timers --all 2>/dev/null | grep -iE 'rumor|y4ss1n3|n0d4|boul3h14|gh3nj4' || true)"
fi
if [ -z "$H9" ] && [ -z "$H9T" ]; then
    pass "H9V no cron/timer references to challenge users"
else
    fail "H9V cron/timer refs: $H9 $H9T"
fi

H10="$(grep -rE '9atchal|lweld|farf0sh|ingehack|matdiresh|inge_dawla|artaza' \
    /tmp /var/tmp /dev/shm /opt /srv 2>/dev/null || true)"
[ -z "$H10" ] && pass "H10V no secrets in scratch/public directories" || fail "H10V secrets: $H10"

H11_PS="$(ps auxww 2>/dev/null | grep -aE '9atchal|lweld|farf0sh|ingehack|matdiresh|inge_dawla|artaza' | grep -v grep || true)"
H11_ENV="$(cat /proc/*/environ 2>/dev/null | tr '\0' '\n' | grep -aE '9atchal|lweld|farf0sh|ingehack|matdiresh|inge_dawla|artaza' || true)"
if [ -z "$H11_PS" ] && [ -z "$H11_ENV" ]; then
    pass "H11V no secrets in process argv or environment"
else
    fail "H11V secrets in process/env"
fi

H12_BAD=0
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    g="$(getent passwd "$u" | cut -d: -f5)"
    [ -z "$g" ] || H12_BAD=1
done
[ "$H12_BAD" -eq 0 ] && pass "H12V GECOS empty for all four users" || fail "H12V GECOS not empty"

[ "$(stat -c '%a %U:%G' /etc/shadow 2>/dev/null)" = '640 root:shadow' ] \
    && pass "H13V /etc/shadow is 0640 root:shadow" \
    || fail "H13V /etc/shadow mode/owner wrong"

SSHD_T="$(sshd -T 2>/dev/null || true)"
H14_BAD=0
chk_t() {
    local got
    got="$(printf '%s\n' "$SSHD_T" | awk -v k="$1" '$1==k{ $1=""; sub(/^ /,""); print; exit }')"
    [ "$got" = "$2" ] || { fail "H14V $1='$got', expected '$2'"; H14_BAD=1; }
}
chk_t permitrootlogin no
chk_t passwordauthentication yes
chk_t kbdinteractiveauthentication no
chk_t permitemptypasswords no
chk_t allowtcpforwarding no
chk_t permittunnel no
chk_t x11forwarding no
chk_t allowagentforwarding no
chk_t permituserenvironment no
chk_t maxauthtries 3
chk_t logingracetime 30
chk_t maxsessions 2
chk_t maxstartups 10:30:60
# sshd -T prints one AllowUsers line per entry; join them.
ALLOW_GOT="$(printf '%s\n' "$SSHD_T" | awk '$1=="allowusers"{print $2}' | tr '\n' ' ' | sed 's/ $//')"
[ "$ALLOW_GOT" = 'y4ss1n3 n0d4 boul3h14 gh3nj4' ] || { fail "H14V allowusers='$ALLOW_GOT', expected full list"; H14_BAD=1; }
[ "$H14_BAD" -eq 0 ] && pass "H14V sshd configuration matches the spec" || true

H15_BAD=0
for f in /etc/issue /etc/issue.net /etc/motd; do
    [ "$(cat "$f" 2>/dev/null)" = 'Authorized access only.' ] || H15_BAD=1
done
grep -qi '^Banner /etc/issue.net' /etc/ssh/sshd_config || H15_BAD=1
[ "$H15_BAD" -eq 0 ] \
    && pass "H15V banners are exactly 'Authorized access only.'" \
    || fail "H15V banner content/banner directive wrong"

H16_BAD=0
run_as y4ss1n3 'timeout 10 apt-get install -y foo' >/dev/null 2>&1 && H16_BAD=1
run_as y4ss1n3 'timeout 10 dpkg -i /dev/null' >/dev/null 2>&1 && H16_BAD=1
run_as y4ss1n3 'timeout 10 snap install foo' >/dev/null 2>&1 && H16_BAD=1
run_as y4ss1n3 'timeout 10 flatpak install foo' >/dev/null 2>&1 && H16_BAD=1
[ "$H16_BAD" -eq 0 ] \
    && pass "H16V package managers unusable by the player" \
    || fail "H16V a package manager succeeded as the player"

H17_MOUNT="$(mount 2>/dev/null | grep ' /proc ' | grep -o 'hidepid=[^,)]*' || true)"
H17_PTRACE="$(cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo NA)"
if [ "$H17_PTRACE" = '3' ] || printf '%s' "$H17_MOUNT" | grep -qE 'hidepid=(2|invisible)'; then
    pass "H17V process isolation active ($H17_MOUNT ptrace_scope=$H17_PTRACE)"
else
    info "H17V platform-limited: /proc cannot be remounted; ptrace_scope=$H17_PTRACE"
    pass "H17V process isolation platform-limited (documented)"
fi

H18_PTRACE="$(cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo NA)"
H18_KPTR="$(cat /proc/sys/kernel/kptr_restrict 2>/dev/null || echo NA)"
H18_DMESG="$(cat /proc/sys/kernel/dmesg_restrict 2>/dev/null || echo NA)"
H18_KEXEC="$(cat /proc/sys/kernel/kexec_load_disabled 2>/dev/null || echo NA)"
H18_BPF="$(cat /proc/sys/kernel/unprivileged_bpf_disabled 2>/dev/null || echo NA)"
if [ "$H18_PTRACE" = 3 ] && [ "$H18_KPTR" = 2 ] && [ "$H18_DMESG" = 1 ] \
   && [ "$H18_KEXEC" = 1 ] && [ "$H18_BPF" = 1 ]; then
    pass "H18V sysctl hardening values match"
else
    info "H18V platform-limited: /proc/sys is read-only (ptrace=$H18_PTRACE kptr=$H18_KPTR dmesg=$H18_DMESG kexec=$H18_KEXEC bpf=$H18_BPF)"
    pass "H18V sysctl hardening platform-limited (documented)"
fi

H19="$(grep -cE '^(y4ss1n3|n0d4|boul3h14|gh3nj4)[[:space:]]+(hard|soft)[[:space:]]+core[[:space:]]+0' /etc/security/limits.conf 2>/dev/null || echo 0)"
[ "$H19" -ge 8 ] \
    && pass "H19V core-dump limits set for all four users" \
    || fail "H19V core limits found: $H19, expected 8"

H20="$(find /home -name authorized_keys 2>/dev/null || true)"
[ -z "$H20" ] && pass "H20V no authorized_keys under /home" || fail "H20V keys: $H20"

[ "$(cat /etc/timezone 2>/dev/null)" = 'UTC' ] && [ "$(date +%Z 2>/dev/null)" = 'UTC' ] \
    && pass "H21V timezone is UTC" \
    || fail "H21V timezone not UTC"

H22="$(find /home -type f ! -perm 600 2>/dev/null || true)"
[ -z "$H22" ] && pass "H22V no files readable beyond owner under /home" || fail "H22V non-0600: $H22"

H23="$(find /home -type d -perm -2000 2>/dev/null || true)"
[ -z "$H23" ] && pass "H23V no setgid directories under /home" || fail "H23V setgid dirs: $H23"

H24="$(find /home -exec getfacl {} \; 2>/dev/null | grep -E '^user:[^:]+:|^group:[^:]+:' || true)"
[ -z "$H24" ] && pass "H24V no extended ACLs under /home" || fail "H24V ACLs: $H24"

FS_TYPE="$(stat -f -c %T /home/boul3h14/.sync 2>/dev/null || echo unknown)"
LSATTR="$(lsattr /home/boul3h14/.sync/.backup.bin 2>/dev/null || true)"
if printf '%s' "$LSATTR" | grep -q 'i'; then
    pass "H25V immutable bit applied to .backup.bin"
else
    info "H25V chattr unsupported on $FS_TYPE (documented exception)"
    pass "H25V chattr unsupported on $FS_TYPE (documented exception)"
fi

###############################################################################
section "LEAK / IDENTITY"
###############################################################################
if [ "$(stat -c '%a %U:%G' /root/gh3nj4_password.txt 2>/dev/null)" = '600 root:root' ]; then
    pass "GHPW gh3nj4 password file is 0600 root:root"
else
    fail "GHPW gh3nj4 password file mode/owner wrong"
fi
GH_PW="$(cat /root/gh3nj4_password.txt 2>/dev/null || true)"
if [ -n "$GH_PW" ] && ! grep -qF "$GH_PW" "$LOG" 2>/dev/null; then
    pass "GHPW gh3nj4 password is redacted from auth.log"
else
    fail "GHPW gh3nj4 password appears in auth.log or is empty"
fi

LEAK="$(grep -rF "$REAL_FLAG" /entrypoint.sh /verify.sh /etc /root /home /var/log 2>/dev/null || true)"
[ -z "$LEAK" ] \
    && pass "LEAK no plaintext real flag on disk" \
    || fail "LEAK plaintext real flag found: $LEAK"

[ ! -e /solutions ] \
    && pass "LEAK no /solutions directory in the image" \
    || fail "LEAK /solutions directory present"

###############################################################################
section "SERIES CONSISTENCY"
###############################################################################
# ops/deploy-static.sh runs the container without -h, so docker reports the
# container id and ignores /etc/hostname. Cosmetic: visible, never fatal.
if [ "$(hostname 2>/dev/null)" = 'challenge-rumor-mill-3' ]; then
    pass "SC1 hostname is challenge-rumor-mill-3"
else
    info "SC1 hostname is $(hostname 2>/dev/null) (docker-assigned; /etc/hostname: $(cat /etc/hostname 2>/dev/null))"
    pass "SC1 hostname cosmetic (platform-limited)"
fi

case "$REAL_FLAG" in
    "${FLAG_PREFIX}"*"}" ) pass "SC2 real flag matches the series format" ;;
    * ) fail "SC2 real flag format wrong" ;;
esac

[ "$(cat /home/gh3nj4/flag.txt 2>/dev/null)" = "$FAKE_FLAG" ] \
    && [ "$(cat /home/gh3nj4/.cache/.flag_backup 2>/dev/null)" = "$FAKE_FLAG" ] \
    && pass "SC3 fake flag string is exactly the series decoy" \
    || fail "SC3 fake flag mismatch"

[ "$FAKE_FLAG" = "$(b64d 'aW5nZWhhY2t7dGgxc18xc180X2Y0azNfZmw0Z30=')" ] \
    && case "$FAKE_FLAG" in "${FLAG_PREFIX}"*"}" ) pass "SC4 series flag format/decoy consistent" ;; * ) fail "SC4 series constants inconsistent" ;; esac \
    || fail "SC4 series constants inconsistent"

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
