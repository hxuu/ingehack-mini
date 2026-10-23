#!/usr/bin/env bash
# Remove a challenge from the Ingehack Mini platform cleanly.
#
# Order of operations for a merged-but-removable challenge (run from the
# maintainer machine, same auth as register-challenge.sh: perms-3 bot with
# challsRead|challsWrite — ADR 0005):
#   1. Soft-remove: PUT the live challenge back with hidden=true so it leaves
#      the player view immediately (rCTF v2 has no per-route "hide").
#   2. --wipe: hard-delete via DELETE /api/v1/admin/challs/:id — the ONLY
#      delete route that exists (v1; docs/research/rctf-v2-api-schema.md).
#   3. Report the manual sweep that no API covers: GHCR image and any running
#      per-team instances (they also expire via timeoutMilliseconds).
#
# After hiding, remove challenges/<category>/<name>/ in a PR so CI stops
# building/re-registering it. Re-merge of the old chall.yaml would unhide it.
#
# Schema source of truth:
#   docs/research/rctf-v2-api-schema.md (extracted from otter-sec/rctf@main).
set -euo pipefail

platform=; challenge_id=; token=; wipe=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) platform=$2; shift 2;;
    --challenge-id) challenge_id=$2; shift 2;;
    --token) token=$2; shift 2;;
    --wipe) wipe=1; shift;;
    *) echo "unknown arg $1" >&2; exit 1;;
  esac
done
[[ $platform && $challenge_id && $token ]] || {
  echo "usage: $0 --platform URL --challenge-id ID --token TOKEN [--wipe]" >&2
  exit 1
}
command -v jq >/dev/null || { echo "need jq" >&2; exit 1; }
command -v python3 >/dev/null || { echo "need python3" >&2; exit 1; }

auth=(-H "Authorization: Bearer $token")

# ---- fetch the live challenge -----------------------------------------------
resp=$(curl -fsS "${auth[@]}" "$platform/api/v2/admin/challs/$challenge_id")
kind=$(echo "$resp" | jq -r .kind)
[[ $kind == "goodChallengeV2" ]] || {
  echo "FAIL: unexpected GET kind '$kind' for '$challenge_id'" >&2
  echo "$resp" | jq . >&2
  exit 1
}
echo "$resp" > /tmp/remove-get.json

# ---- 1. hide: PUT the same payload back with hidden=true --------------------
# The GET data is already in the exact PUT shape (set PUT shape == entity), so
# round-tripping it means nothing else changes. Only field we touch is hidden.
data=$(jq '.data | .hidden = true' /tmp/remove-get.json)
echo "hiding '$challenge_id' at $platform ..."
resp=$(curl -fsS -X PUT "${auth[@]}" -H 'Content-Type: application/json' \
  -d "$data" "$platform/api/v2/admin/challs/$challenge_id")
kind=$(echo "$resp" | jq -r .kind)
case $kind in
  goodChallengeUpdateV2) echo "OK: '$challenge_id' hidden from players";;
  *) echo "FAIL: unexpected response kind '$kind' while hiding:"
     echo "$resp" | jq . >&2
     echo "fallback: set hidden: true in chall.yaml and merge — CI re-registers"
     echo "it with hidden=true."
     exit 1;;
esac

# ---- 2. optional hard delete -------------------------------------------------
if [[ $wipe == 1 ]]; then
  code=$(curl -s -o /tmp/remove-del.json -w '%{http_code}' -X DELETE \
    "${auth[@]}" "$platform/api/v1/admin/challs/$challenge_id")
  if [[ $code == 200 || $code == 204 ]]; then
    echo "OK: '$challenge_id' deleted (v1 route)"
  else
    echo "WARN: v1 delete returned HTTP $code — challenge stays hidden (step 1)" >&2
    jq . /tmp/remove-del.json 2>/dev/null >&2 || true
  fi
fi

# ---- 3. manual sweep the API cannot do --------------------------------------
cat <<'EOF'
Remaining sweep (no API covers these):
  - GHCR image from CI's build — delete in the org's package settings.
  - Running per-team instances stop via timeoutMilliseconds, or
    DELETE /api/v2/admin/challs/:id/instance when acting as that team's admin.
  - Remove challenges/<category>/<name>/ in a PR so CI stops shipping it.
EOF
