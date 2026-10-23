---
name: challenge-review
description: Verify an Ingehack Mini challenge actually works, before merge. Use when an author wants to check their own challenge (point at a solver or describe the intended solve) and when the maintainer reviews a PR that changes anything under challenges/. One skill, both jobs.
---

# challenge-review

Verify that a challenge under `challenges/<category>/<name>/` does what the
author claims, as cheaply as possible. Verification is evidence-based: every
claim below gets an actual response or log line, never a "should work".

## Inputs

- The challenge directory (or a PR diff against one).
- One of:
  - a path to a solver script inside `solution/`, or
  - the author's prose description of the intended solve and expected
    experience (ask for it if neither exists — `solution/` must not be empty).

## Verification ladder (cheapest first, stop as soon as the claim is proven)

1. **Static read** (zero tokens beyond reading): `chall.yaml` complete (expose
   kinds valid: `http` / `https` / `tcp-ssl`; pwn = `tcp-ssl`; instance
   timeout present; concept tags present; every `files[]` handout has a
   `size` field), Dockerfile builds-if-plausible, `${RCTF_FLAG}` placeholder
   appears wherever the flag should be injected. Read `solution/` so every
   later check is pointed at the actual intended path.
2. **Local build**: `docker build .` in the challenge directory. Fail =
   review fails with the build log.
3. **Local run + solve**: run the container locally on a throwaway port; if
   the manifest is instanced, fake the env the instancer would inject
   (e.g. `RCTF_FLAG=unverified-flag-local`) and consume the solver — solver
   script executed or prose steps followed. Confirm the good path yields the
   (local) flag and interaction with the challenge yields a sensible bad-flag
   error.
4. **Shared-instance check** (instanced challenges only, final pre-merge
   step): do NOT run platform plumbing yourself. Report that the challenge is
   owed one real instance on the Challs VM; `docs/status.md` has how the
   maintainer (or CI's registration job) does that. Per-team flag injection
   is only provable there, not locally.

A challenge that passes 1–3 is mergeable for static challenges; instanced
challenges additionally need 4 before players see it.

## Review report

Structure the report as: claim → evidence (command + response) → verdict.
Match the `code-review` conventions this repo's AGENTS.md points at. Reject
with concrete fixes, not vibes.

## Token economy

Batch reads, prefer grep over full-file reads, and never re-run a passing
check. The whole author-side loop should normally fit in a handful of tool
calls over the ladder.
