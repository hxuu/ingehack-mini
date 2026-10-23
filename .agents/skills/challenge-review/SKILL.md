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
   timeout present; concept tags present), every `expose` entry carries
   `shouldDisplay: true` (absent = players see NO instance URLs), and every
   `files[]` handout has either a `path:` committed in `files/` (size
   auto-filled at register) or a `url:` with the real byte-count `size`.
   In a static challenge's description, the URL line maps scheme to port
   exactly (`http://` on the HTTP port, `https://` on the HTTPS port —
   swapped, Traefik 404s; current ports via `docs/status.md`) and its host
   matches the directory name, since that is what CI labels the Traefik
   host. `${RCTF_FLAG}` appears wherever the flag should be injected. Read
   `solution/` so every later check aims at the intended path.
2. **Local build**: `docker build .` in the challenge directory. Fail =
   review fails with the build log.
3. **Local run + solve**: run the container locally on a throwaway port; if
   the manifest is instanced, fake the env the instancer would inject
   (e.g. `RCTF_FLAG=unverified-flag-local`) and consume the solver — solver
   script executed or prose steps followed. Confirm the intended path yields
   the flag and a wrong flag yields a sensible bad-flag response. Handouts:
   `path:` entries open with their solver (`unzip -l` etc.); `url:` entries
   fetch publicly with 200 and byte-size == manifest `size`.
4. **Live-instance check** (instanced challenges only, final pre-merge
   step): do NOT run platform plumbing yourself. Report that the challenge
   is owed one real instance on the Challs VM; `docs/status.md` has how the
   maintainer (or CI's registration job) does that. Per-team flag injection
   is only provable there, not locally.

A challenge that passes 1–3 is mergeable for static challenges; instanced
challenges additionally need 4 before players see it.

## Review report

Structure the report as: claim → evidence (command + response) → verdict.
Reject with concrete fixes, not vibes. The whole author-side loop should
normally fit in a handful of tool calls over the ladder; never re-run a
passing check.
