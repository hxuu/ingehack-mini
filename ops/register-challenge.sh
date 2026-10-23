#!/usr/bin/env bash
# Register a challenge (chall.yaml + GHCR image) on the Ingehack Mini platform
# via the rCTF v2 admin API. Called by .github/workflows/challenges.yml
# (ADR 0005) and usable by hand from the maintainer machine.
#
# Auth: bot admin with challsRead|challsWrite only (perms 3). Never promote
# this token to full admin; rotate by re-promoting a fresh email + one secret
# edit.
set -euo pipefail

platform=; manifest=; image=; token=
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) platform=$2; shift 2;;
    --manifest) manifest=$2; shift 2;;
    --image) image=$2; shift 2;;
    --token) token=$2; shift 2;;
    *) echo "unknown arg $1" >&2; exit 1;;
  esac
done
[[ $platform && $manifest && $image && $token ]] || { echo "missing args" >&2; exit 1; }

command -v jq >/dev/null || { echo "need jq" >&2; exit 1; }
python3 -c 'import yaml' 2>/dev/null || { echo "need PyYAML (pip install pyyaml)" >&2; exit 1; }

# chall.yaml -> rCTF v2 challenge payload.
# Schema notes (docs/status.md + ADR 0003):
#   - files[] handout entries REQUIRE a `size` field each.
#   - instanced challenges carry expose kinds (http/https/tcp-ssl) with
#     per-entry hostPrefix and an instance timeout; the image is $image and
#     the instancer injects the per-team flag over `${RCTF_FLAG}`
#     (GLOSSARY.md: Flag Placeholder).
# TODO(verify): exact PUT /api/v2/admin/challs field names are finalised
# against the live API during the hello-instancer E2E round; the verified
# record lands in docs/status.md and this mapping is corrected there — this
# script is the single place that maps schema.
payload=$(python3 - "$manifest" "$image" <<'PY'
import json, sys, yaml
m = yaml.safe_load(open(sys.argv[1]))
payload = {
    "name": m["name"],
    "challengeIntegrationId": m["challengeIntegrationId"],
    "type": "standardTieBreaker",
    "category": m["category"],
    "description": m["description"],
    "author": m.get("author", "Unknown"),
    "imageUrl": sys.argv[2],
    "scores": {"classic": {"min": m.get("scoreMin", 100), "max": m.get("scoreMax", 500)}},
    "tags": m.get("conceptTags", []),
    "individuallyInstanced": bool(m.get("instanced", False)),
    "files": [
        {"name": f["name"], "path": f["path"], "size": f["size"]}
        for f in m.get("files", [])
    ],
}
print(json.dumps(payload))
PY
)

challenge_id=$(python3 -c 'import sys,yaml;print(yaml.safe_load(open(sys.argv[1]))["challengeIntegrationId"])' "$manifest")

echo "Registering challenge '$challenge_id' at $platform ..."
# TODO(verify): PUT vs POST (update vs create) confirmed live during the
# hello-instancer E2E round; verified record goes to docs/status.md.
curl -fsS -X PUT \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -d "$payload" \
  "$platform/api/v2/admin/challs/$challenge_id"
echo "OK: $challenge_id registered with $image"
