---
name: update-challenge
description: Update an Ingehack Mini challenge after it has shipped. Use when an author wants to change a live challenge's manifest or code (text, points, tags, expose layout, handouts) rather than create a new one. Not for creating challenges — that is `new-challenge`.
---

# update-challenge

Change an existing `challenges/<category>/<name>/` and get the change onto the
platform. The author edits challenge-visible content; the plumbing below
decides how the change travels.

## What kind of change is this? (always ask this first)

1. **Manifest or handout text only** (description, points, tags,
   `releaseTime`, flavor, expose layout) — no rebuild needed. Fast path:
   run `ops/update-challenge.sh --platform https://ctf.ingeniums.club
   --manifest <chall.yaml> --token "$CHALLENGE_BOT_TOKEN"` directly on the
   maintainer machine. Done when the script prints `OK`.
2. **Code or Dockerfile change** — rebuild required. Commit to the challenge
   jobs run CI: merged PR ⇒ new image built, shipped, and re-registered
   (ADR 0005). Static challenges redeploy via `ops/deploy-static.sh`, which
   replaces the running container (`docker rm -f` first). Done = CI workflow
   `challenges` shows the job green for the directory.

Mixing kinds: a PR carrying both is fine — the fast path only saves a rebuild
when the change is genuinely text-only.

## Hard rules

- `${RCTF_FLAG}` placeholder semantics and `challengeIntegrationId`
  immutability still apply (see `new-challenge`).
- Never hand-edit live platform state outside these two scripts — CI and the
  ops scripts are the only writers to the platform.
- A challenge is being retired instead? Use `remove-challenge`.

## Rollback

Git revert + merge rolls the manifest back; CI re-registers the previous
state. Images are immutable and tagged by sha, so rollback never rebuilds.
