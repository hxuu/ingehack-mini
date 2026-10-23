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
payload=$(CHALLENGE_IMAGE="$image" python3 - "$manifest" <<'PY'
import json, os, sys, yaml
m = yaml.safe_load(open(sys.argv[1]))
img = os.environ["CHALLENGE_IMAGE"]

data = {
    "name": m["name"],
    "category": m["category"],
    "author": m.get("author", "Unknown"),
    "description": m["description"],
    "points": {"min": m.get("points", {}).get("min", 100),
               "max": m.get("points", {}).get("max", 500)},
    "tiebreakEligible": m.get("tiebreakEligible", True),
    "hidden": m.get("hidden", False),
    "releaseTime": m.get("releaseTime", None),
    "scoring": m.get("scoring", {"kind": "decay"}),
}
if "tags" in m: data["tags"] = m["tags"]

if "flags" in m:                    # full entries form
    data["flags"] = m["flags"]
elif "flagsDynamicBase" in m:       # per-team flags (instanced challenges)
    data["flags"] = [{"provider": "flags/dynamic",
                      "config": {"base": m["flagsDynamicBase"],
                                 "mode": m.get("flagsDynamicMode", "auto")}}]
elif "flag" in m:                   # single static
    data["flags"] = [{"provider": "flags/static", "config": {"flag": m["flag"]}}]
else:
    sys.exit(f"{sys.argv[1]}: no flag entry (flag / flags / flagsDynamicBase)")

if m.get("instanced"):
    inst = m["instancer"]
    services = json.loads(json.dumps(inst.get("services", {"main": {}})))
    for svc in services.values():
        svc.setdefault("image", img)
    data["instancerConfig"] = {
        "challengeIntegrationId": inst.get("challengeIntegrationId",
                                           m.get("challengeIntegrationId")),
        "timeoutMilliseconds": inst["timeoutMilliseconds"],
        "extendable": inst.get("extendable", False),
        "expose": inst["expose"],
        "config": {"services": services,
                   "networks": inst.get("networks", {}),
                   "volumes": inst.get("volumes", {})},
    }

files = [
    {"name": f["name"], "path": f["path"], "size": f.get("size")}
    for f in m.get("files", [])
]
print(json.dumps({"data": data} | {"filesOnDisk": files}))
PY
)

# handouts with a local path get uploaded to the R2 bucket first
# (POST /api/v2/admin/upload is multipart; response gives name/url/size).
files_json=$(echo "$payload" | jq -c '.filesOnDisk // []')
payload=$(echo "$payload" | jq 'del(.filesOnDisk)')
files_any_local=$(echo "$files_json" | jq -e '[.[] | select(.path != null)] | length' \
  || echo 0)
if [[ "$files_any_local" -gt 0 ]]; then
  echo "FAIL: chall.yaml declares local handouts but the upload wiring is not" \
       "proven yet (POST /api/v2/admin/upload is multipart; bot token HAS" \
       "challsWrite). Register these challenges manually or drop local files for" \
       "now — see docs/research/rctf-v2-api-schema.md §Upload." >&2
  exit 2
fi
online=$(echo "$files_json" | jq -c 'map({name, url: (if .url then .url else "" end), size: (if .size then .size else 0 end)})')
payload=$(echo "$payload" | jq --argjson files "$online" '.data.files = $files')

id=$(python3 -c 'import sys,yaml;m=yaml.safe_load(open(sys.argv[1]));i=m.get("instancer") or {};print(i.get("challengeIntegrationId", m.get("challengeIntegrationId")) or m["name"].lower().replace(" ","-"))' "$manifest")

# ---- pre-PUT validation: instancer config against the LIVE provider schema --
echo "validating instancerConfig against live provider schema ..."
inst_schema_url="$platform/api/v2/admin/instancer/schema"
curl -fsS "$inst_schema_url" -H "Authorization: Bearer $token" -o /tmp/instschema.json
python3 - "$manifest" /tmp/instschema.json <<'PY'
import json, sys, yaml
m = yaml.safe_load(open(sys.argv[1]))
schema_doc = json.load(open(sys.argv[2]))
if not m.get("instanced"): sys.exit(0)
try:
    import jsonschema
except ImportError:
    print("WARN: jsonschema module missing — skipping deep config validation")
    sys.exit(0)
insts = schema_doc["data"]["instancers"]
default = schema_doc["data"].get("defaultInstancer")
chosen = m["instancer"].get("instancerName", default)
entry = next(i for i in insts if i["name"] == chosen)
cfg = {"services": m["instancer"].get("services"), "networks": m["instancer"].get("networks", {}), "volumes": m["instancer"].get("volumes", {})}
jsonschema.validate(cfg, entry["schema"])
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
