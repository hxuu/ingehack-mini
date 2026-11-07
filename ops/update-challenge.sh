#!/usr/bin/env bash
# Update platform metadata for a challenge WITHOUT rebuilding or shipping an
# image (description, points, tags, release time, sort weight, flags, expose
# layout, handouts). Code changes still go through a merged PR: CI rebuilds and
# ships (ADR 0005); ops/deploy-static.sh handles static code deploys, this
# script never runs containers.
#
# The trap here: PUT is a full-entity upsert, so an instanced payload must
# carry working service images there is no rebuild to fall back on. Default
# behaviour reuses the LIVE service images (GET /api/v2/admin/challs/:id),
# i.e. whatever CI shipped last. Pass --image to target a specific tag.
# Adding/removing a service that has no live counterpart REQUIRES --image.
#
# Auth: same perms-3 bot as register (challsRead|challsWrite, ADR 0005).
# Payload builder: ops/chall-payload.py (shared with register).
set -euo pipefail

platform=; manifest=; token=; image=
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) platform=$2; shift 2;;
    --manifest) manifest=$2; shift 2;;
    --token)    token=$2;  shift 2;;
    --image)    image=$2;  shift 2;;
    *) echo "unknown arg $1" >&2; exit 1;;
  esac
done
[[ $platform && $manifest && $token ]] || {
  echo "usage: $0 --platform URL --manifest chall.yaml --token TOKEN [--image IMAGE]" >&2
  exit 1
}
command -v jq >/dev/null || { echo "need jq" >&2; exit 1; }
python3 -c 'import yaml' 2>/dev/null || pip install --quiet pyyaml || pip3 install --quiet pyyaml
[[ -f $manifest ]] || { echo "no such manifest: $manifest" >&2; exit 1; }

auth=(-H "Authorization: Bearer $token")

# ---- manifest payload (shared builder; no image injection by default) -------
instanced=$(python3 -c 'import sys,yaml;m=yaml.safe_load(open(sys.argv[1]));print("true" if m.get("instanced") else "false")' "$manifest")
payload=$(CHALLENGE_IMAGE="${image:-}" python3 ops/chall-payload.py "$manifest")

# handouts with a local path are NOT uploadable here (same gap as register;
# POST /api/v2/admin/upload is multipart and not proven yet).
files_json=$(echo "$payload" | jq -c '.filesOnDisk // []')
payload=$(echo "$payload" | jq 'del(.filesOnDisk)')
files_any_local=$(echo "$files_json" | jq '[.[] | select(.path != null)] | length')
if [[ "$files_any_local" -gt 0 ]]; then
  echo "FAIL: chall.yaml declares local handouts; upload wiring is unproven" \
       "(see register-challenge.sh). Update these manually for now." >&2
  exit 2
fi
online=$(echo "$files_json" | jq -c 'map({name, url: (if .url then .url else "" end), size: (if .size then .size else 0 end)})')
payload=$(echo "$payload" | jq --argjson files "$online" '.data.files = $files')

id=$(python3 -c 'import sys,yaml;m=yaml.safe_load(open(sys.argv[1]));i=m.get("instancer") or {};print(i.get("challengeIntegrationId", m.get("challengeIntegrationId")) or m["name"].lower().replace(" ","-"))' "$manifest")

# ---- instanced + no --image: splice the LIVE service images into the payload
if [[ $instanced == true && -z $image ]]; then
  resp=$(curl -fsS "${auth[@]}" "$platform/api/v2/admin/challs/$id")
  live=$(echo "$resp" | jq -c '.data.instancerConfig.config.services // {}')
  if [[ $live == "{}" && ! $(echo "$resp" | jq -r .kind) == "goodChallengeV2" ]]; then
    echo "FAIL: cannot GET '$id' to reuse live images: $(echo "$resp" | jq -r .kind)" >&2
    exit 1
  fi
  # manifest service without a live counterpart -> no known image -> refuse;
  # otherwise overlay the live image per service key.
  payload=$(UPDATE_LIVE_SERVICES="$live" UPDATE_PAYLOAD="$payload" python3 <<'PY'
import json, os, sys
put = json.loads(os.environ["UPDATE_PAYLOAD"])
live = json.loads(os.environ["UPDATE_LIVE_SERVICES"])
svc = put["data"].get("instancerConfig", {}).get("config", {}).get("services", {})
missing = [k for k, v in svc.items() if not v.get("image") and not live.get(k, {}).get("image")]
if missing:
    sys.exit("services with no image and no live counterpart: " + ",".join(missing))
for k, v in svc.items():
    if live.get(k, {}).get("image"):
        v["image"] = live[k]["image"]
print(json.dumps(put))
PY
) || {
    echo "FAIL: cannot splice live service images — $?" >&2
    echo "fix: pass --image" >&2
    exit 1
  }
  echo "reusing live service images for '$id'"
fi


# ---- PUT (same upsert as register) ------------------------------------------
echo "updating challenge '$id' at $platform ..."
resp=$(curl -fsS -X PUT "${auth[@]}" -H 'Content-Type: application/json' \
  -d "$payload" "$platform/api/v2/admin/challs/$id")
kind=$(echo "$resp" | jq -r .kind)
case $kind in
  goodChallengeUpdateV2) echo "OK: '$id' updated from $manifest";;
  *) echo "FAIL: unexpected response kind '$kind'"; echo "$resp" | jq . >&2; exit 1;;
esac
