#!/usr/bin/env bash
###############################################################################
# verify_solution.sh — automated solver for Rumor Mill #2
# Runs the intended chain as y4ss1n3 inside the container, derives
# boul3h14's password, decrypts the flag, and exits 0 on success.
#
# Usage:  CONTAINER=rumor-mill-2 solutions/verify_solution.sh
###############################################################################
set -euo pipefail

CONTAINER="${CONTAINER:-rumor-mill-2}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

die() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

MANIFEST=""
for f in "$ROOT/challenge.yml" "$ROOT/chall.yaml"; do
    if [ -f "$f" ]; then MANIFEST="$f"; break; fi
done
[ -n "$MANIFEST" ] || die "cannot find challenge.yml or chall.yaml"
REAL_FLAG="$(sed -n 's/^flag_real:[[:space:]]*//p' "$MANIFEST" | head -1 | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
[ -n "$REAL_FLAG" ] || REAL_FLAG="$(sed -n 's/^flag:[[:space:]]*//p' "$MANIFEST" | head -1 | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
[ -n "$REAL_FLAG" ] || die "cannot read the expected flag from $MANIFEST"

as_player() { # command
    docker exec -i -u y4ss1n3 "$CONTAINER" bash -c "$1"
}

su_as() { # target password command
    local target="$1" pw="$2" cmd="$3"
    ( sleep 1.5; printf '%s\n' "$pw" ) | \
        docker exec -i -u y4ss1n3 "$CONTAINER" \
            script -qec "stty -echo; su -c '$cmd' $target" /dev/null 2>&1
}

clean() {
    printf '%s\n' "$1" | tr -d '\r' | sed -e '/^Password: *$/d' -e '/^[[:space:]]*$/d'
}

b64d() { printf '%s' "$1" | base64 -d 2>/dev/null; }

echo "=== Rumor Mill #2 — automated solver ==="

# 1. Stale handover note
ONBOARD="$(as_player 'cat /home/y4ss1n3/onboarding.txt')" \
    || die "cannot read onboarding.txt as y4ss1n3"
OLD_B64="$(printf '%s\n' "$ONBOARD" | awk 'NF==1 && $1 ~ /=$/ {print $1; exit}')"
[ -n "$OLD_B64" ] || die "no base64 password in onboarding.txt"
OLD_PW="$(b64d "$OLD_B64")"
echo "[1] stale password from onboarding: $OLD_PW"

# 2. The stale password must be rejected
OUT="$(su_as n0d4 "$OLD_PW" 'id' || true)"
if printf '%s' "$OUT" | grep -q 'uid='; then
    die "stale n0d4 password still works"
fi
echo "[2] stale password correctly rejected"

# 3. History points at .env
HIST="$(as_player 'cat /home/y4ss1n3/.bash_history')" \
    || die "cannot read .bash_history"
printf '%s' "$HIST" | grep -q '\.env' || die ".bash_history does not point at .env"
echo "[3] .bash_history points at .env"

# 4. Rotated password
ENVC="$(as_player 'cat /home/y4ss1n3/.env')" || die "cannot read .env"
N0_B64="$(printf '%s' "$ENVC" | sed -n 's/^N0D4_B64=//p' | head -1)"
[ -n "$N0_B64" ] || die "N0D4_B64 missing from .env"
N0_PW="$(b64d "$N0_B64")"
echo "[4] rotated n0d4 password: $N0_PW"

OUT="$(clean "$(su_as n0d4 "$N0_PW" 'id')")"
printf '%s' "$OUT" | grep -q 'uid=[0-9]*(n0d4)' || die "cannot su to n0d4"
echo "[5] su n0d4 succeeded"

# 5. Read the parts and their order
N0_README="$(clean "$(su_as n0d4 "$N0_PW" 'cat /home/n0d4/README')")"
printf '%s' "$N0_README" | grep -qF 'join(decode(' || die "n0d4 README missing join rule"

ORDER_B64="$(clean "$(su_as n0d4 "$N0_PW" 'cat /home/n0d4/.part_order')")"
ORDER="$(b64d "$ORDER_B64")"
[ "$ORDER" = '2,3,1' ] || die ".part_order decoded to '$ORDER', expected 2,3,1"
echo "[6] part order: $ORDER"

P1="$(b64d "$(clean "$(su_as n0d4 "$N0_PW" 'cat /home/n0d4/.part1.b64')")")"
P2="$(b64d "$(clean "$(su_as n0d4 "$N0_PW" 'cat /home/n0d4/.part2.b64')")")"
P3="$(b64d "$(clean "$(su_as n0d4 "$N0_PW" 'cat /home/n0d4/.part3.b64')")")"
echo "[7] parts: 1=$P1 2=$P2 3=$P3"

BOUL_PW="${P2}_${P3}_${P1}"
echo "[8] boul3h14 password: $BOUL_PW"

OUT="$(clean "$(su_as boul3h14 "$BOUL_PW" 'id')")"
printf '%s' "$OUT" | grep -q 'uid=[0-9]*(boul3h14)' || die "cannot su to boul3h14"
echo "[9] su boul3h14 succeeded"

# 6. Decode the key and decrypt the flag
KEY_B64="$(clean "$(su_as boul3h14 "$BOUL_PW" 'cat /home/boul3h14/.key.b64')")"
KEY="$(b64d "$KEY_B64")"
[ -n "$KEY" ] || die "empty decryption key"
echo "[10] decryption key: $KEY"

FLAG="$(clean "$(su_as boul3h14 "$BOUL_PW" \
    "cd /home/boul3h14 && openssl enc -d -aes-256-cbc -a -pbkdf2 -in flag.txt -k $KEY")")"

[ "$FLAG" = "$REAL_FLAG" ] || die "flag mismatch: got '$FLAG'"

echo
echo "FLAG: $FLAG"
exit 0
