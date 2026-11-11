#!/usr/bin/env bash
# verify.sh — Cutout invariant suite. Prints PASS/FAIL per check; exits 0
# only when everything passes. Player rows run as uid boul3h14, infra rows
# as root inside the container.
set -uo pipefail

PASS=0
FAIL=0
declare -a FAILURES

hi() { printf '\n== %s ==\n' "$*"; }
ok()  { printf 'PASS: %s\n' "$1"; PASS=$((PASS+1)); }
bad() { printf 'FAIL: %s\n' "$1"; FAIL=$((FAIL+1)); FAILURES+=("$1"); }

PLAYER=boul3h14
as_player() { runuser -u "$PLAYER" -- "$@"; }

# stale triggers from earlier runs would poison both the leak rows (MUST-FAIL
# section runs first) and the player-side writes in the chain — clean first.
rm -f /tmp/*.trigger 2>/dev/null

# ─────────────────────────── MUST FAIL (as player) ───────────────────────────
hi "MUST-FAIL rows (player must be denied)"

check_denied() { # check_denied <desc> <cmd…>
    local desc="$1"; shift
    if as_player "$@" >/dev/null 2>&1; then
        bad "$desc (unexpectedly allowed)"
    else
        ok "$desc"
    fi
}

check_denied "ls /home/ch41n denied"               ls  /home/ch41n
check_denied "ls /home/gh0st denied"               ls  /home/gh0st
check_denied "cat /home/ch41n/ch41n.py denied"     cat /home/ch41n/ch41n.py
check_denied "cat /home/ch41n/fragments/P1 denied" cat /home/ch41n/fragments/P1
check_denied "cat /home/gh0st/flag.txt denied"     cat /home/gh0st/flag.txt

out="$(as_player bash -c 'grep -rE "ingehack|v3rm1l10n|r34l_k3y" /home 2>/dev/null' | head -5)"
[ -z "$out" ] && ok "grep /home (player) empty" || bad "grep /home (player): $out"

out="$(as_player bash -c 'find /home -name fragments -o -name unlocks 2>/dev/null' | head -5)"
[ -z "$out" ] && ok "find /home fragments|unlocks (player) empty" || bad "find /home (player): $out"

PIDANY="$(pgrep -u ch41n -f 'ch41n.py' | head -1)"
if [ -n "$PIDANY" ]; then
    check_denied "daemon fd3 pre-trigger denied (pid $PIDANY)" cat "/proc/$PIDANY/fd/3"
else
    bad "no ch41n.py daemon running"
fi

out="$(ps auxww | grep -E 'ingehack|v3rm1l10n|0f_cust0dy|r34l_k3y' | grep -v 'grep -E' | head -3)"
[ -z "$out" ] && ok "ps argv leak-free" || bad "ps argv leak: $out"

out="$(runuser -u "$PLAYER" -- bash -c 'grep -rE "ingehack|v3rm1l10n|r34l_k3y" /tmp /var/tmp /dev/shm 2>/dev/null' | grep -v '^/tmp/p1.unlock' | head -3)"
[ -z "$out" ] && ok "world-writable dirs clean (player view)" || bad "world dirs leak: $out"

if as_player sudo -n -l >/dev/null 2>&1; then bad "sudo allowed"; else ok "sudo not allowed"; fi

# ─────────────────────────── MUST SUCCEED (as player) ────────────────────────
hi "MUST-SUCCEED rows (player-visible puzzle surface)"

out="$(as_player cat /tmp/p1.unlock 2>&1)"
[ "$out" = "start" ] && ok "/tmp/p1.unlock reads 'start'" || bad "p1.unlock: '$out'"

FILES="$(as_player find /opt/vendor-tool -type f)"
echo "$FILES" | grep -q '.part1' && echo "$FILES" | grep -q '.part2' && \
    echo "$FILES" | grep -q 'vendor-tool.conf' && ok "/opt files present" || bad "/opt files: $FILES"
out="$(as_player cat /opt/vendor-tool/lib/.part1 2>&1)"
echo "$out" | grep -q 'v3rm1l10n' && echo "$out" | grep -q '/var/lib/vendor-tool/.ledger' \
    && ok ".part1 content" || bad ".part1: $out"
out="$(as_player cat /opt/vendor-tool/share/.part2 2>&1)"
echo "$out" | grep -q '0bs1d14n' && ok ".part2 content" || bad ".part2: $out"

readarray -t LABELS < <(awk '!/^#/ && NF==3 {print $1}' /var/lib/vendor-tool/.ledger)
readarray -t ROLES  < <(awk '!/^#/ && NF==3 {print $3}' /var/lib/vendor-tool/.ledger)
LINES="$(awk '!/^#/ && NF==3' /var/lib/vendor-tool/.ledger | wc -l)"
KEYROWS="$(awk '$3=="key" && $2=="2048"' /var/lib/vendor-tool/.ledger | wc -l)"
[ "$LINES" = "6" ] && [ "$KEYROWS" = "1" ] \
    && ok "ledger: 6 rows, exactly one '2048 key'" \
    || bad "ledger rows=$LINES keyrows=$KEYROWS"

# trigger chain — the six daemons, one holder per label (all fd3 reads are
# same-uid by design: run as the player)
P1LABEL=""; declare -A ROLE_OF
for i in 0 1 2 3 4 5; do
    L="${LABELS[$i]}"
    printf 'start' > "/tmp/$L.trigger"
    hp=""
    for _ in $(seq 1 40); do
        hp="$(as_player cat "/run/cutout/$L.holder" 2>/dev/null | tr -d '[:space:]')"
        [ -n "$hp" ] && break
        sleep 0.1
    done
    if [ -n "$hp" ]; then
        c="$(as_player python3 -c "
try: print(open('/proc/$hp/fd/3','rb').read().decode(errors='replace'))
except Exception: print('')" 2>/dev/null)"
        if [ "$c" = "ingehack{" ]; then P1LABEL="$L"; fi
    fi
    rm -f "/tmp/$L.trigger"
done
[ -n "$P1LABEL" ] && ok "P1 identified via public 'start' unlock ($P1LABEL)" \
    || bad "no daemon accepted 'start'"

# full crypto chain (triggered via holders as the player — same fd path)
hi "trigger chain + crypto (player reads holder fd during window)"

cat > /tmp/.cutout-verify-chain.py <<'PY'
import os, sys, time

EXPECTED = b"ingehack{ch41n_0f_cust0dy}"
labels = open("/var/lib/vendor-tool/.ledger").read()
rows = [l.split() for l in labels.splitlines() if l.strip() and not l.startswith("#")]
labels = [r[0] for r in rows]
roles = [r[2] for r in rows]

def holder(label, timeout=6.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            return int(open(f"/run/cutout/{label}.holder").read().strip())
        except (OSError, ValueError):
            time.sleep(0.2)
    return None

def blob(hp, timeout=9.0):
    """Poll /proc/<holder pid>/fd/3 — same-uid only. Empty read is the
    keeper's /dev/null placeholder (fd not handed over yet), not a reply."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            with open(f"/proc/{hp}/fd/3", "rb") as fh:
                d = fh.read()
            if d:
                return d
        except OSError:
            pass
        time.sleep(0.15)
    return None

pids = {l: holder(l) for l in labels}
assert all(pids.values()), pids

# trigger ALL first pass: P1's public code is 'start'
for l in labels:
    open(f"/tmp/{l}.trigger", "w").write("start")
time.sleep(1.8)

data = {l: blob(pids[l]) for l in labels}
closes = [l for l, b in data.items() if b is None]
assert len(data) - len(closes) >= 1, data
p1 = [l for l, b in data.items() if b == b"ingehack{"]
assert len(p1) == 1, data
p1label = p1[0]
for l in labels:
    # harden: close triggers of labels that already answered
    if data.get(l) is not None and l != p1label:
        try: os.unlink(f"/tmp/{l}.trigger")
        except OSError: pass

# mid-chain: everything accepts 'ingehack{' EXCEPT P5
for l in labels:
    if l == p1label:
        continue
    open(f"/tmp/{l}.trigger", "w").write("ingehack{")
time.sleep(1.8)
data = {l: blob(pids[l]) for l in labels}
data[p1label] = b"ingehack{"
closed = [l for l, b in data.items() if b is None]
assert len(closed) == 1, data
p5label = closed[0]
open(f"/tmp/{p5label}.trigger", "w").write("ch41n_")
time.sleep(1.8)
data[p5label] = blob(pids[p5label])

# clean triggers now so world-dir leak rows stay quiet
for l in labels:
    try: os.unlink(f"/tmp/{l}.trigger")
    except OSError: pass

def xor_frag(b, key, offset, ln):
    return bytes(x ^ key[i % len(key)] for i, x in enumerate(b[offset:offset+ln]))

combined = (open('/opt/vendor-tool/lib/.part1').readline().strip()
            + open('/opt/vendor-tool/share/.part2').readline().strip()).encode()
real = b"r34l_k3y_0bs1d14n"

key_label = [l for l, r in zip(labels, roles) if r == "key"][0]
assert len(data[key_label]) == 4096, data
k = xor_frag(data[key_label], combined, 2048, len(real))
assert k == real, (k, real)

frags = {}
for l in labels:
    b = data.get(l)
    if b and len(b) == 4096 and l != key_label:
        f = xor_frag(b, real, 1024, 17)     # decode over max length, trim later
        if f.startswith(b"ch41n_"):   frags["P4"] = f[:6]
        if f.startswith(b"0f_"):      frags["P5"] = f[:11]

assert frags.get("P4") == b"ch41n_", frags
assert frags.get("P5") == b"0f_cust0dy}", frags
flag = b"ingehack{" + frags["P4"] + frags["P5"]
okflag = flag == EXPECTED
print("DECRYPTED:", flag.decode())
print("CRYPTO_OK" if okflag else "CRYPTO_MISMATCH")
sys.exit(0 if okflag else 2)
PY
runuser -u boul3h14 -- python3 /tmp/.cutout-verify-chain.py
RC=$?
rm -f /tmp/.cutout-verify-chain.py
[ $RC -eq 0 ] && ok "XOR chain + flag assembly" || bad "XOR chain/flag (rc=$RC)"
sleep 0.3

# ───────────────────────────── ALSO VERIFY ───────────────────────────────────
hi "also-verify rows"

grep -q 'pam_faillock.so preauth' /etc/pam.d/su && grep -q 'pam_faillock.so authfail' /etc/pam.d/su \
    && ok "pam_faillock in /etc/pam.d/su" || bad "pam_faillock missing"

# SUID allowlist compare (distro-standard set on this image + nothing else)
SUID_ALL="$(find / -xdev -perm -4000 -type f 2>/dev/null | sort)"
read -r -d '' SUID_ALLOW <<'EOF' || true
/bin/mount
/bin/su
/bin/umount
/sbin/mount
/sbin/umount
/usr/bin/chfn
/usr/bin/chsh
/usr/bin/expiry
/usr/bin/gpasswd
/usr/bin/mount
/usr/bin/newgrp
/usr/bin/passwd
/usr/bin/su
/usr/bin/umount
/usr/lib/openssh/ssh-keysign
/usr/lib/snapd/snap-confiner
/usr/lib/dbus-1.0/dbus-daemon-launch-helper
/usr/bin/sudo
/usr/lib/eject/dvdram
EOF
SUID_BAD="$(comm -23 <(printf '%s\n' "$SUID_ALL" | sed '/^$/d') <(printf '%s\n' "$SUID_ALLOW" | sed '/^$/d' | sort) | head -5)"
[ -z "$SUID_BAD" ] && ok "no unexpected SUID" || bad "unexpected SUID: $SUID_BAD"

GEC="$(getent passwd boul3h14 ch41n gh0st | awk -F: '{print $1"="length($5)}')"
echo "$GEC" | grep -q 'boul3h14=0' && echo "$GEC" | grep -q 'ch41n=0' && echo "$GEC" | grep -q 'gh0st=0' \
    && ok "GECOS empty" || bad "GECOS: $GEC"

for u in /home/*; do
    m="$(stat -c '%a' "$u")"
    [ "$m" = "700" ] || bad "home mode $u=$m"
done
ok "home dirs 700"

BADF="$(find /home -type f ! -perm 600 ! -perm 700 2>/dev/null | head -5)"
[ -z "$BADF" ] && ok "all /home files 600/700" || bad "bad file modes: $BADF"

if mount | grep ' /proc ' | grep -q 'hidepid=[12]'; then
    bad "/proc mounted with hidepid!=0"
else
    ok "hidepid=0"
fi

SYS="$(cat /etc/sysctl.d/99-cutout-hardening.conf 2>/dev/null)"
echo "$SYS" | grep -q 'ptrace_scope = 3' && ok "ptrace_scope=3 pinned in sysctl.d" \
    || bad "ptrace_scope config missing"
echo "$SYS" | grep -q 'core_pattern = /dev/null' && ok "core_pattern pinned" \
    || bad "core_pattern config missing"

grep -q 'Authorized access only' /etc/issue && grep -q 'Authorized access only' /etc/motd \
    && ok "issue/motd banner" || bad "banner missing"

[ -d /etc/cron.d ] && bad "/etc/cron.d present" || ok "no cron jobs"

T="$(systemctl list-units --type=timer --state=active --no-legend 2>/dev/null | awk '{print $1}' | grep -vE '^(systemd-tmpfiles-clean|cutout-watchdog|apt-daily|apt-daily-upgrade|e2scrub_all|e2scrub-|fstrim|logrotate|man-db|dpkg-db-backup|update-notifier-download|motd-news)\.timer$|^timers.target$' | head -3)"
[ -z "$T" ] && ok "only allowed timers active" || bad "unexpected timers: $T"

# don't leave trigger files behind: they are player-owned and poison any
# solution script that runs right after this one.
rm -f /tmp/*.trigger 2>/dev/null

hi "summary"
if [ "$FAIL" -eq 0 ]; then
    printf 'verify.sh: ALL %s checks PASS\n' "$PASS"
    exit 0
else
    printf 'verify.sh: %s PASS, %s FAIL\n' "$PASS" "$FAIL"
    printf 'Failures:\n'
    for f in "${FAILURES[@]}"; do printf '  - %s\n' "$f"; done
    exit 1
fi
