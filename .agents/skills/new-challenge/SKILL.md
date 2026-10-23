---
name: new-challenge
description: Create, update, or ship an Ingehack Mini challenge. Use when a challenge author wants to start a new challenge in this repo, change an existing one, or produce the package that makes it go live. The author only needs to know WHAT the challenge is — this skill handles everything about how it runs.
---

# new-challenge

One skill for the whole author lifecycle: **new → update → ship**. The author
supplies ideas, code, and flavor; this skill supplies all platform plumbing.
An author should never need to know what a Mapped Port, an Expose, or rCTF is
and should never touch the live VMs.

## Live facts

Never hardcode ports, hosts, or tokens. Read `docs/status.md` for current VM
paths, mapped ports, and hostnames before doing anything that touches the
platform. GLOSSARY.md defines the domain words used below.

## Input interview (always do this first)

Ask the author, and don't scaffold until answered:

1. **Name** — kebab-case, used as the directory and challenge id.
2. **Category** — pwn / web / rev / crypto / forensics / misc. Categories map
   one-to-one to directories under `challenges/`.
3. **Instanced or static?** Static (shared server, e.g. most crypto/forensics)
   vs. instanced (per-team container, e.g. pwn/web serving files). If unsure,
   recommend based on parallel-team use and whether each team needs an isolated
   copy.
4. **Concept tag(s)** — the first-year CS concept this teaches (e.g. HTTP
   Protocol, Data Encoding, Browser Trust Boundaries). rCTF takes these as
   free-form tags.
5. **Difficulty + flavor text** — beginner-aware: flavor text that points at
   the concept without spoiling.
6. **Flag format** — always `${RCTF_FLAG}` in author code; the instancer bakes
   the per-team value at launch. Static challenges use a fixed flag decided at
   ship time.

## Scaffold

Create `challenges/<category>/<name>/` with:

- `Dockerfile` — category-typical base and layout (e.g. pwn: minimal Debian +
  socat/ynetd + compiled binary; web: whatever the stack needs; rev: nothing
  served, just handouts).
- `chall.yaml` — the human-side manifest (exact contract:
  `ops/register-challenge.sh` maps it to the rCTF v2 upsert; see
  `docs/research/rctf-v2-api-schema.md`): `name`, `author`, `category`,
  `description` (markdown), `points: {min,max}`, `tags` (concept tags),
  `tiebreakEligible`, `hidden`/`releaseTime`, flags (`flag:` static OR
  `flagsDynamicBase` per-team), `files[]` handouts (`name`, `path`, `size`),
  and for instanced challenges: `instanced: true`, `instancer` block with
  `challengeIntegrationId` (stable id, never changes after launch),
  `timeoutMilliseconds`, `extendable`, `expose[]` (kinds `http`, `https`,
  `tcp-ssl` — pwn is always `tcp-ssl`; each entry: `hostPrefix`,
  `containerName`, `containerPort`, `title`), and `services` (tiny-instancer
  config: mind `mem_limit` default "6m", `read_only: true`,
  `cap_drop: ['ALL']` baked-in defaults that break most services — declare
  what you need). CI injects the `image:` at register time.
  ship step turns into platform config.
- `src/` — challenge code. Where the flag placeholder is used, it is
  literally the string `${RCTF_FLAG}`; the instancer replaces it from the
  challenge env at launch.
- `solution/` — how it's meant to be solved: a solver script if the author has
  one, otherwise a plain prose walkthrough. `challenge-review` consumes this;
  it is mandatory.

Keep scaffolds small and idiomatic per category — a 1st-year should solve it,
the author should barely review the plumbing.

## Update mode

Re-running this skill on an existing directory updates `chall.yaml` /
Dockerfile / src as requested, re-deriving everything else from the manifest.
Never hand-edit live platform state to "test" a change — the platform is fed
only by ship.

## Ship mode

Produce the CI artifact: the workflow at `.github/workflows/challenges.yml`
builds `challenges/<category>/<name>/` on merge and pushes the image to public
GHCR, then registers the challenge via the rCTF v2 admin API. So ship = make
sure of exactly two things:

1. The directory builds: `docker build .` succeeds and the entrypoint runs.
2. `chall.yaml` is complete — every field the platform needs, including the
   `size` field for every `files[]` handout entry (rCTF v2 requires it; ADR
   0003).

Then the PR is the author's deliverable. Merged PR = the challenge goes live;
no release step exists.
