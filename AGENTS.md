# Ingehack Mini — agent instructions

## What this repo is

Ingehack Mini is a jeopardy CTF for first-year CS students at
ingeniums.club, running on rCTF v2 across two OpenScaler VMs behind
Cloudflare. This repo holds both the live infrastructure record and the
challenge authoring workflow. **Merge = live**: a merged PR touching
`challenges/<category>/<name>/` builds and ships the image when the
challenge has a runtime (instanced or static container), and registers,
deploys, or retires the challenge on the platform
(`.github/workflows/challenges.yml`, ADR 0005). Challenge images never leave
the VM; authors work through git alone and need no SSH key, token, or VM
access.

## Where things live

| Path | Role |
|---|---|
| `challenges/<category>/<name>/` | One challenge. `chall.yaml` is its single source of truth; `Dockerfile` + `src/` exist when it runs a container (a description-only challenge has neither), `files/` downloadable handouts, `solution/` the required solver. |
| `.agents/skills/` | Challenge lifecycle skills (list below). Single source of truth; other harness directories symlink here. |
| `docs/status.md` | Live infrastructure state: VMs, DNS/TLS, mapped ports, gotchas, verified records. **Source of truth for anything running.** |
| `GLOSSARY.md` | Domain language — read before naming anything in records or prose. |
| `docs/adr/` | Decisions and non-negotiables; cite by number. |
| `docs/research/` | rCTF v2 API schema notes the ops scripts depend on. |
| `ops/` | Maintainer-side register/update/remove/deploy scripts. CI calls them; a hand-run needs a maintainer token. |
| `.github/workflows/challenges.yml` | The deploy pipeline: detect directory diff → build/ship when the challenge has a runtime → register or retire. |

For infrastructure work, read in this order: `docs/status.md`, then
`GLOSSARY.md`, then the ADRs.

## Skills in this repo

Inside this repo: challenge lifecycle skills live in `.agents/skills/` —
`new-challenge` (read before creating or editing anything under
`challenges/`), `update-challenge` (change a live challenge),
`remove-challenge` (retire one), `challenge-review` (verify a challenge
actually works — author-side check and PR review are the same skill), and
`pr` (use when creating a PR). Platform state follows the repo: a merged PR
that creates, changes, or deletes a challenge directory ships, re-registers,
or retires it automatically (the `challenges` workflow).

Harnesses that need their own directory symlink in here (`.claude` →
`.agents`, `CLAUDE.md` → `AGENTS.md`); `.agents/skills/` is the single source
of truth.

## Branching (authors)

**A branch is scratch; a merge is everyone's.** Authors branch freely off
`main` — a branch never touches the platform, and CI only ever detects a
merged PR's directory diff (`HEAD^..HEAD` in `challenges.yml`). Never commit
author work on `main`: if you find the author there, move them to a branch
named after their GitHub login (`gh api user --jq .login`) before editing;
the `pr` skill's Branch guard has the exact procedure and opens the PR. Other PRs
merging meanwhile only matter when they overlap the same directory — that
shows up as an ordinary git conflict: rebase onto the new `main`, resolve,
and re-run `challenge-review` locally (its earlier verdicts are stale the
moment the base moved). Force-push during an open review only invalidates
reviewed evidence; avoid it while a review is in flight.

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`hxuu/ingehack-mini`) via the `gh` CLI; PRs not used as a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage labels, label string equals role name (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `GLOSSARY.md` + `docs/adr/`. See `docs/agents/domain.md`.

## Hard rules

- Zero dollars, no payment verification with any vendor (ADR 0002/0004).
- Secrets live on the VMs or in GitHub Actions secrets — never in this repo
  (ADR 0004).
- Never point DNS at the VM IP; use the gateway hostname or tunnel CNAME.
