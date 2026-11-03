#!/usr/bin/env bash
###############################################################################
# verify_solution.sh — automated solver for Rumor Mill #3 — The Liars' Club
#
# Follows section 7 exactly: starts as y4ss1n3, rejects the lies, rebuilds the
# boul3h14 password from the auth log, and decrypts the real flag.
#
# Usage:  CONTAINER=rumor-mill-3-test solutions/verify_solution.sh
#
# The script never reads a flag as root: every file access is performed with
# `docker exec -u y4ss1n3` (or as the target of a real `su`).
###############################################################################
set -euo pipefail

CONTAINER="${CONTAINER:-rumor-mill-3-test}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

die() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

MANIFEST=""
for f in "$ROOT/challenge.yml" "$ROOT/chall.yaml"; do
    [ -f "$f" ] && MANIFEST="$f" && break
done
[ -n "$MANIFEST" ] || die "cannot find challenge.yml or chall.yaml"

EXPECTED="$(sed -n 's/^flag_real:[[:space:]]*//p' "$MANIFEST" | head -1 | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
[ -n "$EXPECTED" ] || EXPECTED="$(sed -n 's/^flag:[[:space:]]*//p' "$MANIFEST" | head -1 | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
FAKE="$(sed -n 's/^flag_fake:[[:space:]]*//p' "$MANIFEST" | head -1 | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
[ -n "$EXPECTED" ] || die "cannot read the expected flag from $MANIFEST"
[ -n "$FAKE" ] || FAKE='ingehack{th1s_1s_4_f4k3_fl4g}'

as_y4() { docker exec -i -u y4ss1n3 "$CONTAINER" bash -c "$1"; }

clean_out() {
    printf '%s\n' "$1" | tr -d '\r' | sed -e '/^Password: *$/d' -e '/^su: /d'
}

su_cmd() { # user password command
    local u="$1" pw="$2" cmd="$3" b64 out rc
    b64="$(printf '%s' "$cmd" | base64 -w0)"
    out="$( ( sleep 1.1; printf '%s\n' "$pw" ) | \
        docker exec -i -u y4ss1n3 "$CONTAINER" \
            script -qec "stty -echo; su -c 'echo $b64 | base64 -d | bash' $u" /dev/null 2>&1 )"
    rc=$?
    printf '%s' "$out"
    return "$rc"
}

echo "=== Rumor Mill #3 — The Liars' Club — automated solver ==="

# 1. y4ss1n3's onboarding lie.
ONBOARD="$(as_y4 'cat /home/y4ss1n3/onboarding.txt')" || die "cannot read onboarding.txt"
B64="$(printf '%s\n' "$ONBOARD" | sed -n 's/^[[:space:]]*\([A-Za-z0-9+/=]\{8,\}\)[[:space:]]*$/\1/p' | head -1)"
[ -n "$B64" ] || die "onboarding.txt has no base64 value"
ONBOARD_PW="$(printf '%s' "$B64" | base64 -d)"
[ "$ONBOARD_PW" = 'matdiresh' ] || die "onboarding decodes to '$ONBOARD_PW', expected matdiresh"
echo "[1] onboarding decodes to: $ONBOARD_PW"

# 2. The onboarding password must fail for n0d4.
BAD="$(su_cmd n0d4 "$ONBOARD_PW" 'id' || true)"
printf '%s' "$BAD" | grep -q 'uid=[0-9]*(n0d4)' && die "onboarding password unexpectedly opened n0d4"
echo "[2] su n0d4 with onboarding password rejected"

# 3. nohup.out leaks the real n0d4 password.
NOHUP="$(as_y4 'cat /home/y4ss1n3/nohup.out')" || die "cannot read nohup.out"
N0D4_PW="$(printf '%s\n' "$NOHUP" | sed -n 's/.*new password: //p' | head -1)"
[ -n "$N0D4_PW" ] || die "nohup.out has no password line"
echo "[3] nohup.out leaks the real n0d4 password"

# 4. Real su to n0d4.
OUT="$(su_cmd n0d4 "$N0D4_PW" 'id')" || die "su n0d4 failed"
printf '%s' "$OUT" | grep -q 'uid=[0-9]*(n0d4)' || die "su n0d4 did not yield uid=n0d4"
echo "[4] su n0d4 succeeded"

# 5. README lie + the two parts.
N0DATA="$(su_cmd n0d4 "$N0D4_PW" 'cat /home/n0d4/README /home/n0d4/.part1.b64 /home/n0d4/.part2.b64')" \
    || die "cannot read n0d4's files"
printf '%s' "$N0DATA" | grep -q 'decode(.part2)' || die "README composition rule missing"
P1B64="$(printf '%s\n' "$N0DATA" | grep -o 'OWF0Y2hhbA==' | head -1)"
P2B64="$(printf '%s\n' "$N0DATA" | grep -o 'bHdlbGQ=' | head -1)"
[ -n "$P1B64" ] && [ -n "$P2B64" ] || die "could not read both password parts"
PART1="$(printf '%s' "$P1B64" | base64 -d)"
PART2="$(printf '%s' "$P2B64" | base64 -d)"
[ -n "$PART1" ] && [ -n "$PART2" ] || die "password parts do not decode"
echo "[5] parts recovered: .part1 and .part2"

# 6. The README's order is a lie.
WRONG="${PART2}${PART1}"
BAD="$(su_cmd boul3h14 "$WRONG" 'id' || true)"
printf '%s' "$BAD" | grep -q 'uid=[0-9]*(boul3h14)' && die "README order unexpectedly opened boul3h14"
echo "[6] README order (part2+part1) rejected"

# 7. The auth log carries the separator and the true order.
LOG="$(as_y4 'cat /var/log/rumor/auth.log')" || die "cannot read auth.log"
SEP_LINE="$(printf '%s\n' "$LOG" | grep -F 'printf "%s_%s" "9atchal" "lweld"' | head -1)"
[ -n "$SEP_LINE" ] || die "auth.log separator line missing"
L1="$(printf '%s' "$SEP_LINE" | sed -n 's/.*"%s_%s" "\([^"]*\)" "\([^"]*\)".*/\1/p')"
L2="$(printf '%s' "$SEP_LINE" | sed -n 's/.*"%s_%s" "\([^"]*\)" "\([^"]*\)".*/\2/p')"
[ -n "$L1" ] && [ -n "$L2" ] || die "could not parse the separator line"
BOUL_PW="${L1}_${L2}"
echo "[7] auth.log gives the separator and order"

# 8. Real su to boul3h14.
OUT="$(su_cmd boul3h14 "$BOUL_PW" 'id')" || die "su boul3h14 failed"
printf '%s' "$OUT" | grep -q 'uid=[0-9]*(boul3h14)' || die "su boul3h14 did not yield uid=boul3h14"
echo "[8] su boul3h14 succeeded"

# 9. The flag.txt/confession redirection.
BFLAG="$(su_cmd boul3h14 "$BOUL_PW" 'cat /home/boul3h14/flag.txt /home/boul3h14/.confession')" \
    || die "cannot read boul3h14's notes"
printf '%s' "$BFLAG" | grep -q 'the flag moved' || die "flag.txt does not point at .confession"
printf '%s' "$BFLAG" | grep -q '/home/gh3nj4/.cache/.flag_backup' || die ".confession destination missing"
echo "[9] flag.txt -> .confession -> gh3nj4 (claimed)"

# 10. The claimed destination is a decoy.
DENIED="$(su_cmd boul3h14 "$BOUL_PW" 'cat /home/gh3nj4/.cache/.flag_backup' || true)"
if printf '%s' "$DENIED" | grep -qF 'ingehack{'; then
    die "boul3h14 could read gh3nj4's decoy backup"
fi
echo "[10] gh3nj4 backup is unreadable to boul3h14"

# 11. find cannot locate the flag names.
FIND="$(su_cmd boul3h14 "$BOUL_PW" 'find / -name .flag_backup -o -name .backup.bin 2>/dev/null' || true)"
if printf '%s' "$FIND" | grep -q 'flag_backup\|backup.bin'; then
    die "find exposed a flag path: $FIND"
fi
echo "[11] find cannot enumerate either backup"

# 12. The recovery key is a decoy.
REC="$(su_cmd boul3h14 "$BOUL_PW" 'cat /home/boul3h14/.recovery.txt')" || die "cannot read .recovery.txt"
printf '%s' "$REC" | grep -q 'matdiresh_key' || die ".recovery.txt missing the old key"
BAD_DEC="$(su_cmd boul3h14 "$BOUL_PW" "openssl enc -d -aes-256-cbc -a -pbkdf2 -k matdiresh_key -in /home/boul3h14/.sync/.backup.bin" 2>&1 || true)"
if printf '%s' "$BAD_DEC" | grep -qF 'ingehack{'; then
    die "the recovery key decrypted the real blob"
fi
echo "[12] the recovery key does not decrypt the blob"

# 13. The bash history only plants the fake.
HIST="$(su_cmd boul3h14 "$BOUL_PW" 'cat /home/boul3h14/.bash_history')" || die "cannot read history"
printf '%s' "$HIST" | grep -qF "$FAKE" || die "history does not contain the fake flag"
printf '%s' "$HIST" | grep -qF "$EXPECTED" && die "history contains the real flag"
echo "[13] history only contains the fake flag"

# 14. verify_gh3nj4.txt confirms the fake.
VGH="$(su_cmd boul3h14 "$BOUL_PW" 'cat /home/boul3h14/verify_gh3nj4.txt')" || die "cannot read verify_gh3nj4.txt"
printf '%s' "$VGH" | grep -qF "$FAKE" || die "verify_gh3nj4.txt does not name the fake"
echo "[14] verify_gh3nj4.txt confirms the decoy"

# 15. audit_copy.log is doctored.
AUDIT="$(su_cmd boul3h14 "$BOUL_PW" 'cat /home/boul3h14/audit_copy.log')" || die "cannot read audit_copy.log"
printf '%s' "$AUDIT" | grep -q 'n0d4/.sync' || die "audit_copy.log does not point at the decoy"
printf '%s' "$AUDIT" | grep -q 'boul3h14/.sync' && die "audit_copy.log still contains the real path"
echo "[15] audit_copy.log points only at the decoy"

# 16. The real log points at the real path.
printf '%s' "$LOG" | grep -qE 'openssl.*boul3h14/\.sync/\.backup\.bin' || die "real log missing the openssl line"
printf '%s' "$LOG" | grep -qF 'real flag only in boul3h14/.sync' || die "real log missing the confirmation"
echo "[16] the real log names boul3h14/.sync"

# 17. The strings header tells the truth about the source, and the flag is
#     still encrypted.
STRINGS="$(su_cmd boul3h14 "$BOUL_PW" 'strings /home/boul3h14/.sync/.backup.bin')" \
    || die "cannot run strings"
printf '%s' "$STRINGS" | grep -qF 'SYNCED_FROM:/home/gh3nj4/.cache/.flag_backup' || die "SYNCED_FROM missing"
printf '%s' "$STRINGS" | grep -qF 'SYNCED_AT:2026-11-02T11:00:02Z' || die "SYNCED_AT missing"
printf '%s' "$STRINGS" | grep -qF 'ingehack{' && die "plaintext flag appears in strings output"
echo "[17] .backup.bin header verified; flag is encrypted"

# 18. The key file.
NOTES="$(su_cmd boul3h14 "$BOUL_PW" 'cat /home/boul3h14/.sync/.notes.txt')" || die "cannot read .notes.txt"
KEY_B64="$(printf '%s\n' "$NOTES" | grep -o 'bHdlbGRfZWxfZmFyZjBzaA==' | head -1)"
[ -n "$KEY_B64" ] || die ".notes.txt does not contain the base64 key"
KEY="$(printf '%s' "$KEY_B64" | base64 -d)"
echo "[18] key recovered from .notes.txt"

# 19. Decrypt the real blob.
FLAG="$(su_cmd boul3h14 "$BOUL_PW" "openssl enc -d -aes-256-cbc -a -pbkdf2 -k '$KEY' -in /home/boul3h14/.sync/.backup.bin" \
    | tr -d '\r' | tail -1)"
[ -n "$FLAG" ] || die "decryption produced nothing"
printf '%s' "$FLAG" | grep -qF 'ingehack{' || die "decryption did not produce a flag: $FLAG"

[ "$FLAG" = "$EXPECTED" ] || die "flag mismatch: got '$FLAG', expected '$EXPECTED'"

echo "[19] decrypted the real flag"
echo
echo "FLAG: $FLAG"
exit 0
