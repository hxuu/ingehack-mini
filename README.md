# ingehack-mini

A jeopardy CTF for first-year CS students, run by
[ingeniums.club](https://ingeniums.club). This repo holds both the
infrastructure documentation *and* the challenge authoring workflow — challenge
images never leave the organization's VM, and "merged PR" means "live for
players".

> [!NOTE]
> This is a private repo during preparation. Challenges stay out of public
> registries by design — the CI ships built images straight onto the challenge
> VM. Publish/open the repo after the event if desired.

## How it works, in one breath

Two VMs: a **platform VM** running [rCTF v2](https://rctf.osec.io) behind a
Cloudflare tunnel, and a **challenge VM** running rCTF v2's Docker instancer
(traefik + redis + tiny-instancer). Per-team instances are spawned on demand
with a **per-team flag baked at launch**. Everything operational lives in the
docs; challenge authors never touch any of it.

## Repo tour

```.
├── challenges/<category>/<name>/     # The authoring body of work
│   ├── chall.yaml                    #   the manifest (single source of truth)
│   ├── Dockerfile + src/             #   the challenge itself
│   └── solution/                     #   solver script or walkthrough (required)
├── docs/status.md                    # Live infra state + verified records
├── GLOSSARY.md                       # Domain vocabulary
├── docs/adr/                         # Decisions incl. the CI/CD contract
├── docs/research/                    # rCTF v2 API schema research etc.
├── ops/                              # Maintainer-side deploy/register scripts
├── .github/workflows/challenges.yml  # Merged PR ⇒ live challenge
└── .agents/skills/                   # Challenge lifecycle skills, for any agent harness
```

## I'm writing a challenge

Clone this repo, launch your agent inside it, and say *"new challenge"*.

The [`new-challenge`](/.agents/skills/new-challenge) skill interviews you (name,
category, instanced or not, concept tags, flavor text), scaffolds
`challenges/<category>/<name>/`, and manages updates. You write the challenge;
it writes the plumbing.

Before you open the PR:

```sh
# call this with your agent — it verifies without hand-holding
"run challenge-review on my directory"
```

The [`challenge-review`](/.agents/skills/challenge-review) skill checks the
manifest, builds the image, and runs your solver path locally. **Merge = live.**
CI builds your image, ships it inside the challenge VM, and registers it on the
platform — no hosting, no ports, no platform API in your face.

> [!IMPORTANT]
> Flags: write the literal string `${RCTF_FLAG}` in challenge code for per-team
> flags (the instancer injects the team's value at launch); `chall.yaml` sets
> the flag provider/base. Static challenges declare a fixed
> `flag: ingehack{...}` right in the manifest.

## I'm updating a challenge

Launch your agent in the repo and say *"update challenge <name>"* — the
[`update-challenge`](/.agents/skills/update-challenge) skill routes the change:

```sh
# text-only change (description, points, tags, release time, expose layout)
ops/update-challenge.sh --platform https://ctf.ingeniums.club \
  --manifest challenges/<category>/<name>/chall.yaml --token "$CHALLENGE_BOT_TOKEN"
```

Text-only manifest edits re-register directly, no rebuild. Code or Dockerfile
changes go through a merged PR — CI rebuilds, ships, and re-registers. Rollback
is `git revert` + merge.

## I'm removing a challenge

Say *"remove challenge <name>"* — the
[`remove-challenge`](/.agents/skills/remove-challenge) skill runs:

```sh
# hide it from players immediately (no v2 delete route exists)
ops/remove-challenge.sh --platform https://ctf.ingeniums.club \
  --challenge-id <id> --token "$CHALLENGE_BOT_TOKEN" [--wipe]
```

`--wipe` hard-deletes via the v1 API (use only when the challenge must not
exist). Then delete `challenges/<category>/<name>/` in a PR so CI stops
shipping it — re-merging the directory would restore it. See
[docs/status.md](/docs/status.md) for the full procedure.

## I'm running the infra

Start reading here, in order:

1. [`docs/status.md`](/docs/status.md) — live VMs, DNS/TLS, mapped ports,
   gotchas, and the running list of verified-records. **It is the source of
   truth.**
2. [`GLOSSARY.md`](/GLOSSARY.md) — Platform, Instancer, Expose, Mapped Port…
   so you and the scripts say the same words.
3. [`docs/adr/0002`, `0004`, `0005`](/docs/adr) — the non-negotiables:

- **Zero dollars, no payment verification**, with any vendor.
- **Secrets live on the VMs or in GitHub Actions secrets** — never in this repo.
- **Never point DNS at an IP**, only gateway hostnames or the tunnel CNAME.

The maintainer's daily tools are `ops/register-challenge.sh` (manual challenge
registration) and `ops/deploy-static.sh` (static challenge deploys); CI calls
both for you. The event-day kill switch (`registrationsEnabled: false`) is a
two-line routine at the top of `docs/status.md`.

## Key facts at a glance

| What | Where / value |
|---|---|
| Player platform | `https://ctf.ingeniums.club` (CF tunnel, orange) |
| Challenge instances | `https://<prefix>-<uid>.challs.ingeniums.club:<mapped-port>` |
| Exposed kinds | `http`, `https`, `tcp-ssl` (raw `tcp` is auto-upgraded) |
| CI/CD | [`challenges.yml`](/.github/workflows/challenges.yml) — build → `docker load` over SSH → register/deploy |
| Bot credentials | `ci-bot@…` with `challsRead\|challsWrite` (perms 3) only; token in Actions secret |
| Load profile | Platform verified at ~800 rps reads with p95 < 200 ms (250 concurrent) |

## Reporting a bug

Open an issue and do _not_ paste tokens, VM IPs, or logs containing auth
headers. Secrets are infra-side only; anything player-visible should be in the
challenge description, not in code you paste around.
