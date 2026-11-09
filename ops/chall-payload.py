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
    "scoring": m.get("scoring", {"kind": "decay"}),
}
if "tags" in m: data["tags"] = m["tags"]

# hidden, releaseTime, and sortWeight are opt-in: omit the key to leave the
# platform value alone. rCTF's upsert keeps the current value when a key is
# undefined and only clears it on an explicit null, so a value set in the
# admin UI survives CI re-registration. Declare the field in chall.yaml to
# override the platform value explicitly.
if "hidden" in m: data["hidden"] = m["hidden"]
if "releaseTime" in m: data["releaseTime"] = m["releaseTime"]
if "sortWeight" in m: data["sortWeight"] = m["sortWeight"]

# requires: [challenge-id, ...] keeps a challenge invisible to a team until it
# has solved every listed challenge (a series). Opt-in like the fields above:
# omit the key to leave the platform value alone. The check runs in the
# Platform's participant query, not here; this only declares the dependency.
if "requires" in m: data["requires"] = m["requires"]

# `adminBot: <file>` attaches a platform admin-bot handler. The file (e.g.
# admin-bot.ts) is the trusted Challenge source for the admin-bots/rctf-ts
# provider; the API validates it against the live worker and derives the
# inputs/timeout from it at save time.
admin_bot = (m.get("adminBot") or "").strip()
if admin_bot:
    bot_path = os.path.join(os.path.dirname(os.path.abspath(manifest)), admin_bot)
    if not os.path.isfile(bot_path):
        sys.exit(f"{manifest}: admin-bot source missing: {bot_path}")
    data["adminBotConfig"] = {"code": open(bot_path, encoding="utf-8").read().strip()}

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
    # shouldDisplay defaults OFF in rCTF's schema (optional, no default) —
    # a manifest that omits it makes rCTF hide ALL endpoint URLs from players
    # (filterInstanceEndpoints). Default it ON here; opt out per-expose.
    expose = [{**e, "shouldDisplay": e.get("shouldDisplay", True)}
              for e in inst["expose"]]
    data["instancerConfig"] = {
        "challengeIntegrationId": inst.get("challengeIntegrationId",
                                           m.get("challengeIntegrationId")),
        "timeoutMilliseconds": inst["timeoutMilliseconds"],
        "extendable": inst.get("extendable", False),
        "expose": expose,
        "config": {"services": services,
                   "networks": inst.get("networks", {}),
                   "volumes": inst.get("volumes", {})},
    }

# files entries: `path` = local file under the challenge dir (uploaded by
# register-challenge.sh via POST /api/v2/admin/upload); `url` = already-hosted
# attachment (e.g. on attachments.ingeniums.club/R2), no upload, `size` required.
files = [{"name": f["name"],
          **({"path": f["path"]} if "path" in f else {"url": f["url"]}),
          "size": f.get("size")}
         for f in m.get("files", [])]
print(json.dumps({"data": data} | {"filesOnDisk": files}))
