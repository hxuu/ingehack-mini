# ingehack mini

A jeopardy CTF for first-year CS students, run by
[ingeniums.club](https://ingeniums.club). This repo holds both the
infrastructure documentation *and* the challenge authoring workflow — challenge
images never leave the organization's VM, and "merged PR" means "live for
players" (created, updated, *and* deleted: retirement is automatic too).

> [!NOTE]
> This is a private repo during preparation. Challenge images never touch
> public registries — CI ships them straight onto the challenge VM. Publish
> after the event if desired.

## How it works, in one breath

Two VMs: a **platform VM** running [rCTF v2](https://rctf.osec.io) behind a
Cloudflare tunnel, and a **challenge VM** running rCTF v2's Docker instancer
(traefik + redis + tiny-instancer). Per-team instances are spawned on demand
with a **per-team flag baked at launch**; shared challenges are static
containers behind the same traefik. A challenge can also be
**description-only** (`container: false`) — description, flag, and optional
handouts, no container at all, for tasks whose answer lives elsewhere.
Everything operational lives in the docs; challenge authors never touch any
of it.

## Prerequisites

To author and review challenges you need:

- **git** and **Docker** — Docker is for local build/run checks before you
  push (`docker build .`)
- an **agent harness** that reads `.agents/skills/` (or the `CLAUDE.md`
  symlink, which points at [`AGENTS.md`](/AGENTS.md)), e.g.
  [OpenCode](https://github.com/sst/opencode) or Claude Code

No tokens, no SSH keys, no platform access — authors work entirely through
git. Maintainer credentials (bot token, CI SSH key) live in GitHub Actions
secrets only.

## Repo tour

```
├── challenges/<category>/<name>/     # The authoring body of work
│   ├── chall.yaml                    #   the manifest (single source of truth)
│   ├── Dockerfile + src/             #   container challenges only
│   ├── files/                        #   downloadable handouts (optional)
│   └── solution/                     #   solver script or walkthrough (required)
├── docs/status.md                    # Live infra state + verified records
├── GLOSSARY.md                       # Domain vocabulary
├── docs/adr/                         # Decisions incl. the CI/CD contract
├── docs/research/                    # rCTF v2 API schema research etc.
├── ops/                              # Maintainer-side deploy/register scripts
├── .github/workflows/challenges.yml  # Merged PR ⇒ create/update/delete, live
└── .agents/skills/                   # Challenge lifecycle skills, for any agent harness
```

## I'm writing a challenge

Clone this repo, launch your agent inside it, and say *"new challenge"*.

The [`new-challenge`](/.agents/skills/new-challenge) skill interviews you (name,
category, instanced or not, concept tags, flavor text), scaffolds
`challenges/<category>/<name>/`, and manages updates. You write the challenge;
it writes the plumbing.

Before you open the PR, have your agent verify the work:

```sh
"run challenge-review on my directory"
```

The [`challenge-review`](/.agents/skills/challenge-review) skill checks the
manifest, builds the image when there is one, and runs your solver path
locally. **Merge = live.** For container challenges, CI builds your image,
ships it inside the challenge VM, and registers or deploys it; a
description-only challenge is registered as metadata.

> [!IMPORTANT]
> Flags: write the literal string `${RCTF_FLAG}` in challenge code for per-team
> flags (the instancer injects the team's value at launch); `chall.yaml` sets
> the flag provider/base. Static challenges declare a fixed
> `flag: ingehack{...}` right in the manifest.

> [!TIP]
> Renaming: instanced challenges keep their id (pinned by
> `challengeIntegrationId`) — a display rename is safe. A static challenge's
> id **is** its `name`; renaming it migrates platform state (see the
> `new-challenge` skill's Update mode).

## I'm updating a challenge

Launch your agent in the repo and say *"update challenge <name>"* — the
[`update-challenge`](/.agents/skills/update-challenge) skill routes the change:

- **Text-only** manifest edits (description, points, tags, release time, expose
  layout) skip the rebuild via a fast path the skill decides on.
- **Code or Dockerfile** changes go through a merged PR — CI rebuilds, ships,
  and re-registers. Rollback is `git revert` + merge.

Platform writes go through CI or the ops scripts only — never hand-edit live
state to "test" something; test locally instead.

## I'm removing a challenge

Say *"remove challenge <name>"* — but note the simplest correct form: a PR
that **deletes** `challenges/<category>/<name>/` retires the challenge
automatically when merged (hide + wipe + container teardown). For an out-of-band
pull or emergency, the [`remove-challenge`](/.agents/skills/remove-challenge)
skill drives [`ops/remove-challenge.sh`](/ops/remove-challenge.sh) by hand.
Hand-running needs a **maintainer admin token** — `$CHALLENGE_BOT_TOKEN`
exists only as a GitHub Actions secret.

## I'm running the infra

Start reading here, in order:

1. [`docs/status.md`](/docs/status.md) — live VMs, DNS/TLS, mapped ports,
   gotchas, and the running list of verified records. **It is the source of
   truth.**
2. [`GLOSSARY.md`](/GLOSSARY.md) — Platform, Instancer, Expose, Mapped Port…
   so you and the scripts say the same words.
3. [`docs/adr/`](/docs/adr) — the non-negotiables:

- **Zero dollars, no payment verification**, with any vendor (ADR 0002/0004).
- **Secrets live on the VMs or in GitHub Actions secrets** — never in this
  repo (ADR 0004).
- **Never point DNS at an IP**, only gateway hostnames or the tunnel CNAME.

The maintainer's daily tools are `ops/register-challenge.sh` (manual challenge
registration) and `ops/deploy-static.sh` (static challenge deploys); CI calls
both for you. The event-day kill switch (`registrationsEnabled: false`) is a
two-line routine at the top of `docs/status.md`.

## Key facts at a glance

| What | Where / value |
|---|---|
| Player platform | `https://ctf.ingeniums.club` (CF tunnel) |
| Shared challenge URLs | `http(s)://<name>.challs.ingeniums.club:<mapped-port>` — scheme follows the port |
| Per-team instance URLs | `https://<prefix>-<uid>.challs.ingeniums.club:<mapped-port>` |
| Expose kinds | `http`, `https`, `tcp-ssl` |
| Lifecycle | [`challenges.yml`](/.github/workflows/challenges.yml) — merge ⇒ create / update / delete, automatically |
| Current mapped ports & QA state | [`docs/status.md`](/docs/status.md) — they rotate per provider; no other doc hardcodes them |
| Load profile | Platform verified at ~800 rps reads with p95 < 200 ms (250 concurrent) |

## Reporting a bug

Open an issue and do _not_ paste tokens, VM IPs, or logs containing auth
headers. Secrets are infra-side only; anything player-visible should be in the
challenge description, not in code you paste around.
