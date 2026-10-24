---
name: new-challenge
description: Create, update, or ship an Ingehack Mini challenge. Use when a challenge author wants to start a new challenge in this repo, change an existing one, or produce the package that makes it go live.
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

Ask the author, and scaffold only once all six are answered:

1. **Name** — kebab-case, used as the directory and challenge id.
2. **Category** — pwn / web / rev / crypto / forensics / misc. Categories map
   one-to-one to directories under `challenges/`.
3. **Runtime** — one of three:
   - **Instanced** — per-team container(s), e.g. pwn/web serving files.
     Manifest: `instanced: true` plus an `instancer` block.
   - **Static container** — one shared server, e.g. most crypto/forensics.
     Manifest: `instanced: false` (container is default).
   - **Description-only** — no service at all; the description, flag, and
     optional handouts are the whole challenge (e.g. OSINT whose answer lives
     elsewhere, or a "read this / decode that" task). Manifest:
     `instanced: false` + `container: false`.
   If unsure between static and instanced, recommend based on parallel-team
   use and whether each team needs an isolated copy. Prefer description-only
   over shipping a dummy container.
4. **Concept tag(s)** — the first-year CS concept this teaches (e.g. HTTP
   Protocol, Data Encoding, Browser Trust Boundaries). rCTF takes these as
   free-form tags.
5. **Difficulty + flavor text** — beginner-aware: flavor text that points at
   the concept without spoiling.
6. **Flag format** — instanced: author code uses the literal string
   `${RCTF_FLAG}` (the instancer bakes the per-team value at launch);
   static: a fixed flag decided at ship time.

## Scaffold

Create `challenges/<category>/<name>/` with:

- `Dockerfile` — only for instanced/static-container challenges;
  category-typical base and layout (e.g. pwn: minimal Debian + socat/ynetd +
  compiled binary; web: whatever the stack needs; rev: nothing served, just
  handouts). A description-only challenge has no `Dockerfile` and no `src/`.
- `chall.yaml` — the human-side manifest; the platform only ever sees it
  through `ops/register-challenge.sh`, which maps it to the rCTF v2 upsert
  (that script plus `docs/research/rctf-v2-api-schema.md` is the exact
  contract). Fields it needs: `name`, `author`, `category`, `description`
  (markdown), `points: {min,max}`, `tags` (concept tags), `tiebreakEligible`,
  flag (`flag:` static OR `flagsDynamicBase` per-team), `files[]` handouts,
  and for instanced challenges `instanced: true` plus an `instancer` block.
  Description-only challenges add `container: false` (default is `true` for
  `instanced: false`); `instanced: true` always means a container.
  Copy the shape from the exemplars instead of writing from memory:
  - `challenges/misc/sanity-check/` — static, plain page
  - `challenges/misc/hello-shared/` — static, shared-instance flavor
  - `challenges/misc/hello-instancer/` — instanced, all three expose kinds
  - `challenges/misc/sanity-check-2/` and `-3/` — the two handout forms
  CI injects the `image:` at register time.
- Gotchas not visible in the schema doc: the instancer's `services` block
  bakes in `mem_limit: "6m"`, `read_only: true`, `cap_drop: ['ALL']`
  defaults that break most real services — declare what you need. Pwn always
  uses expose kind `tcp-ssl`. Each `expose` entry carries
  `shouldDisplay: true` (rCTF treats absent as hidden and shows players NO
  instance URLs; `chall-payload.py` defaults it on — write it down anyway).
  Static-container challenges are visible to players only through the URL
  line baked into their `description`: scheme follows the port — the mapped
  HTTP port takes `http://`, the mapped HTTPS port takes `https://`; swapped,
  Traefik answers 404. Read the current mapped ports from `docs/status.md`.
  Description-only challenges have no URL line and no Traefik host at all.
- `src/` — challenge code. Where the flag placeholder is used, it is
  literally the string `${RCTF_FLAG}`.
- `files/` handouts, two forms in `files[]`:
  - `path:` — committed with the challenge; register uploads it and
    auto-fills `size` from the file on disk.
  - `url:` — already hosted on `https://attachments.ingeniums.club` (a
    maintainer uploads it once via the admin upload API); `name` and the
    real `size` are required here.
- `solution/` — how it's meant to be solved: a solver script if the author has
  one, otherwise a plain prose walkthrough. `challenge-review` consumes this;
  it is mandatory.

Keep scaffolds small and idiomatic per category — a 1st-year should solve it,
the author should barely review the plumbing.

## Update mode

Re-running this skill on an existing directory updates `chall.yaml` /
Dockerfile / src as requested, re-deriving everything else from the manifest.
Manifest-text-only tweaks skip the rebuild through the `update-challenge`
skill's fast path. Renaming a live challenge: instanced ids are pinned by
`challengeIntegrationId`, so a display rename is safe; a static challenge's
id IS its `name` — re-register under the new name, then hide + wipe the old
id with the `remove-challenge` skill. Taking a challenge off outright: a
merged PR that deletes its directory retires it automatically — see
`remove-challenge`. Test changes locally — platform writes
go through CI or the ops scripts, and live state is never a playground.

## Ship mode

Produce the CI artifact: the workflow at `.github/workflows/challenges.yml`
builds `challenges/<category>/<name>/` on merge, ships the image straight to
the challs VM over SSH, registers the challenge via the bot token, and for
static-container challenges deploys it behind the challs Traefik (http and
https both). Description-only challenges skip build/ship/deploy — CI registers
their metadata and handouts only. So ship = make sure of one criterion,
outside the repo:

1. CI run `challenges` is green for the directory AND `GET
   https://ctf.ingeniums.club/api/v2/challs` lists the challenge — its
   `files[]` for handouts, its displayed URLs matching the manifest's
   description.

For container challenges, local `docker build .` succeeding is the pre-push
sanity check, not the definition of done; description-only challenges have
nothing to build. Merged PR (or a maintainer push to main) = the challenge
goes live; no release step exists.
