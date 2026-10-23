#!/usr/bin/env python3
# Shared chall.yaml -> rCTF v2 payload builder. One source of truth for the
# manifest contract; ops/register-challenge.sh and ops/update-challenge.sh
# both shell out to this. See docs/research/rctf-v2-api-schema.md.
#
# Usage: chall-payload.py <chall.yaml>
#   CHALLENGE_IMAGE env var is injected into instanced services[*].image when
#   set. Prints the payload JSON ({"data": {...}, "filesOnDisk": [...]}) or
#   exits non-zero with a message.
import json, os, sys, yaml

m = yaml.safe_load(open(sys.argv[1]))
img = os.environ.get("CHALLENGE_IMAGE", "")
manifest = sys.argv[1]

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
    sys.exit(f"{manifest}: no flag entry (flag / flags / flagsDynamicBase)")

if m.get("instanced"):
    inst = m["instancer"]
    services = json.loads(json.dumps(inst.get("services", {"main": {}})))
    if img:
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

files = [{"name": f["name"], "path": f["path"], "size": f.get("size")}
         for f in m.get("files", [])]
print(json.dumps({"data": data} | {"filesOnDisk": files}))
