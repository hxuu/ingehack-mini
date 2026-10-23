---
name: remove-challenge
description: Remove or retire a merged, live Ingehack Mini challenge. Use when a shipped challenge must be taken off the platform — pulled, broken, or withdrawn. Not for editing a live challenge — that is `update-challenge`.
---

# remove-challenge

Take a challenge that already went live (merged PR) off the platform, cleanly.
rCTF v2 has no v2 delete route — the only hard delete is v1's
`DELETE /api/v1/admin/challs/:id` (`docs/research/rctf-v2-api-schema.md`) — so
removal is hide-first, wipe-optional, sweep-manual.

## Procedure

1. **Hide (mandatory)**: `ops/remove-challenge.sh --platform
   https://ctf.ingeniums.club --challenge-id <id> --token
   "$CHALLENGE_BOT_TOKEN"`. It PUTs the live challenge back with
   `hidden=true` — done when it prints `OK: ... hidden from players`.
   Do not stop here and edit platform state by hand.
2. **Wipe (only when the challenge must not exist)**: rerun with `--wipe`.
   Order makes the wipe safe: hide already succeeded, so a wipe failure
   leaves the challenge hidden, not half-deleted. Done = `OK: ... deleted
   (v1 route)`.
3. **Sweep (manual, report to the maintainer in the PR)**:
   - delete the GHCR image in the org's package settings;
   - running per-team instances expire via `timeoutMilliseconds` (or
     `DELETE /api/v2/admin/challs/:id/instance` acting per admin team);
   - merge the PR that deletes `challenges/<category>/<name>/` so CI stops
     building and registering it.

## The one direction to watch

Re-merging the challenge directory from git history restores and un-hides it.
If a challenge must stay dead, also delete the directory in the same PR as
step 3, and never restore it without intent.

Prefer verify-only on a throwaway target first: the script is new — smoke-test
it on the QA `qa-pipeline-chall` (scheduled for deletion anyway) before
trusting it on a live challenge.
