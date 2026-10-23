#!/usr/bin/env bash
# Register/update a challenge on the Ingehack Mini platform via the rCTF v2
# admin API. Called by .github/workflows/challenges.yml (ADR 0005) and usable
# by hand from the maintainer machine.
#
# Auth: bot admin with challsRead|challsWrite only (perms 3, ADR 0005). Never
# promote this token beyond that; rotate by re-promoting a fresh email + one
# GitHub secret edit.
#
# Schema source of truth:
#   docs/research/rctf-v2-api-schema.md (extracted from otter-sec/rctf@main).
set -euo pipefail

platform=; manifest=; image=; token=
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) platform=$2; shift 2;;
    --manifest) manifest=$2; shift 2;;
    --image)    image=$2;  shift 2;;
    --token)    token=$2;  shift 2;;
    *) echo "unknown arg $1" >&2; exit 1;;
  esac
done
[[ $platform && $manifest && $image && $token ]] || { echo "missing args" >&2; exit 1; }
command -v jq >/dev/null || { echo "need jq" >&2; exit 1; }
python3 -c 'import yaml' 2>/dev/null || pip install --quiet pyyaml || pip3 install --quiet pyyaml
python3 -c 'import jsonschema' 2>/dev/null || pip install --quiet jsonschema || true

# ---- build the exact rCTF v2 upsert payload from chall.yaml ----------------
# chall.yaml contract (challenges/<category>/<name>/chall.yaml):
#   name, author, category, description, points{min,max}, tags[],
#   tiebreakEligible?, hidden?, releaseTime?, scoring?
#   flags: either
#     flag: ingehack{...}                          (single static flag), or
#     flagsFlagProvider / flagsFlagConfig          (full entry), or
#     flagsDynamicBase / flagsDynamicMode          (per-team minted flags)
#   files: [{name, path(local file to upload), size(optional; filled if absent)}]
#   instanced: bool; when true:
#     challengeIntegrationId, instancer{timeoutMilliseconds, extendable,
#       expose:[{kind, hostPrefix, containerName, containerPort, title?}],
#       services: {...tiny-instancer config.services...}}
# CI injects --image as services[*].image.
# The builder lives in ops/chall-payload.py — shared with update-challenge.sh.
payload=$(CHALLENGE_IMAGE="$image" python3 ops/chall-payload.py "$manifest")

# handouts: entries with a local `path` are uploaded first (multipart
# POST /api/v2/admin/upload, field name `files`, one per request), then every
# handout -- local and pre-hosted alike -- is attached as {name, url, size}.
# The upload provider is `uploads/r2` (publicBaseUrl
# https://attachments.ingeniums.club); dedup is by SHA-256, so re-registering
# an unchanged file returns the same url. `url` entries (already hosted, e.g.
# dropped onto the bucket by a maintainer) ride through unchanged.
files_json=$(echo "$payload" | jq -c '.filesOnDisk // []')
payload=$(echo "$payload" | jq 'del(.filesOnDisk)')
mandir=$(cd "$(dirname "$manifest")" && pwd)

export MANDIR="$mandir" PLATFORM="$platform" AUTH_TOKEN="$token" HANDOUTS="$files_json"
attached=$(python3 - <<'PY'
import json, os, subprocess, sys

mandir, platform, token = os.environ["MANDIR"], os.environ["PLATFORM"], os.environ["AUTH_TOKEN"]
entries = json.loads(os.environ["HANDOUTS"])
out = []
for entry in entries:
    name = entry["name"]
    if "path" in entry:
        p = os.path.join(mandir, entry["path"])
        if not os.path.isfile(p):
            raise SystemExit(f"FAIL: handout file missing: {p}")
        size = entry.get("size") or os.path.getsize(p)
        print(f"uploading handout {name} ({size} bytes) ...", file=sys.stderr, flush=True)
        r = json.loads(subprocess.check_output([
            "curl", "-fsS", "-X", "POST", f"{platform}/api/v2/admin/upload",
            "-H", f"Authorization: Bearer {token}",
            "-F", f"files=@{p};filename={name}",
        ]))
        if r.get("kind") != "goodFilesUploadV2":
            raise SystemExit(f"FAIL: upload kind {r.get('kind')!r} for {name}: {r}")
        try:
            url = next(i["url"] for i in r["data"] if i["name"] == name)
        except StopIteration:
            raise SystemExit(f"FAIL: no url returned for {name}")
        out.append({"name": name, "url": url, "size": size})
    else:
        out.append({"name": name, "url": entry["url"], "size": entry.get("size") or 0})
print(json.dumps(out))
PY
)
payload=$(echo "$payload" | jq --argjson files "$attached" '.data.files = $files')

id=$(python3 -c 'import sys,yaml;m=yaml.safe_load(open(sys.argv[1]));i=m.get("instancer") or {};print(i.get("challengeIntegrationId", m.get("challengeIntegrationId")) or m["name"].lower().replace(" ","-"))' "$manifest")

# ---- pre-PUT validation: PAYLOAD's instancer config vs LIVE provider schema -
echo "validating instancerConfig against live provider schema ..."
curl -fsS "$platform/api/v2/admin/instancer/schema" \
  -H "Authorization: Bearer $token" -o /tmp/instschema.json
echo "$payload" > /tmp/chall-payload.json
python3 - /tmp/chall-payload.json /tmp/instschema.json <<'PY'
import json, sys
put = json.load(open(sys.argv[1]))
schema_doc = json.load(open(sys.argv[2]))
if not put["data"].get("instancerConfig"): sys.exit(0)
try:
    import jsonschema
except ImportError:
    print("WARN: jsonschema module missing — skipping deep config validation")
    sys.exit(0)
insts = schema_doc["data"]["instancers"]
default = schema_doc["data"].get("defaultInstancer")
chosen = put["data"]["instancerConfig"].get("instancer", default)
entry = next(i for i in insts if i["name"] == chosen)
jsonschema.validate(put["data"]["instancerConfig"]["config"], entry["schema"])
print("instancer config validated against", chosen, "schema")
PY

# ---- upsert (create when the id is missing — same PUT) ---------------------
echo "registering challenge '$id' at $platform ..."
curl -fsS -X PUT \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -d "$payload" \
  "$platform/api/v2/admin/challs/$id" > /tmp/put-resp.json
kind=$(jq -r .kind /tmp/put-resp.json)
case "$kind" in
  goodChallengeUpdateV2) echo "OK: '$id' registered/updated with $image";;
  *) echo "FAIL: unexpected response kind '$kind'"; jq . /tmp/put-resp.json; exit 1;;
esac
