# Ingehack Mini — agent instructions

Platform docs: `docs/status.md` (live state), `GLOSSARY.md` (domain
language), `docs/adr/` (topology rationale).

## Skills in this repo

Inside this repo: challenge lifecycle skills live in `.agents/skills/` —
`new-challenge` (read before creating or editing anything under
`challenges/`), `update-challenge` (change a live challenge),
`remove-challenge` (retire one), `challenge-review` (verify a challenge
actually works — author-side check and PR review are the same skill), and
`pr` (use when creating a PR). Platform state follows the repo: a merged PR
that creates, changes, or deletes a challenge directory ships, re-registers,
or retires it automatically (the `challenges` workflow).

Harnesses that need their own directory (e.g. `.claude/skills/`) symlink into
`.agents/skills/` — that is the single source of truth.

## Branching (authors)

**A branch is scratch; a merge is everyone's.** Authors branch freely off
`main` — a branch never touches the platform, and CI only ever detects a
merged PR's directory diff (`HEAD^..HEAD` in `challenges.yml`). Other PRs
merging meanwhile only matter when they overlap the same directory — that
shows up as an ordinary git conflict: rebase onto the new `main`, resolve,
and re-run `challenge-review` locally (its earlier verdicts are stale the
moment the base moved). Force-push during an open review only invalidates
reviewed evidence; avoid it while a review is in flight.

## Hard rules

- Zero dollars, no payment verification with any vendor (ADR 0002/0004).
- Secrets live on the VMs or in GitHub Actions secrets — never in this repo
  (ADR 0004).
- Never point DNS at the VM IP; use the gateway hostname or tunnel CNAME.
