---
name: update-challenge
description: Update an Ingehack Mini challenge after it has shipped. Use when an author wants to change a live challenge's manifest or code (text, points, tags, expose layout, handouts) rather than create a new one. Not for creating challenges — that is `new-challenge`.
---

# update-challenge

Change an existing `challenges/<category>/<name>/` and get the change onto the
platform. Creating one is `new-challenge`; taking one down is
`remove-challenge`.

## What kind of change is this? (always ask this first)

1. **Manifest or handout text only** (description, points, tags,
   `releaseTime`, flavor, expose layout) — no rebuild needed. Fast path:
   run `ops/update-challenge.sh --platform https://ctf.ingeniums.club
   --manifest <chall.yaml> --token <token>` on the maintainer machine. Done
   when the script prints `OK`.
   Environment gotcha worth caching: `$CHALLENGE_BOT_TOKEN` exists only in
   GitHub Actions secrets, never locally — manual writes authenticate with a
   maintainer admin token.
2. **Code or Dockerfile change** — rebuild required. Commit and merge a PR:
   CI jobs build the new image, ship, and re-register it (ADR 0005). Static
   challenges redeploy via `ops/deploy-static.sh`, which replaces the running
   container (a `docker rm -f` gap of a few seconds is part of the swap).
   Done = CI workflow `challenges` green for the directory AND the change
   visible in `GET /api/v2/challs`.
3. **Renaming a live challenge** — the semantics live in `new-challenge`
   Update mode: instanced display rename is safe (`challengeIntegrationId`
   pins the id); a static rename is a migration — re-register under the new
   name, then retire the old id through `remove-challenge`.

Mixing kinds 1 and 2 in one PR is fine — the fast path only saves a rebuild
when the change is genuinely text-only.

## Hard rules

- `${RCTF_FLAG}` placeholder semantics and `challengeIntegrationId`
  immutability still apply (see `new-challenge`).
- CI and the ops scripts are the only writers to the platform.

## Rollback

Git revert + merge rolls the manifest back; CI re-registers the previous
state. Images are immutable and tagged by sha, so rollback never rebuilds.
