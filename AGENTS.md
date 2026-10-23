# Ingehack Mini — agent instructions

Platform docs: `docs/status.md` (live state), `GLOSSARY.md` (domain
language), `docs/adr/` (topology rationale).

## Skills in this repo

- `.agents/skills/new-challenge/` — read before creating or editing anything
  under `challenges/`; it owns scaffold, update, and ship.
- `.agents/skills/challenge-review/` — verify a challenge actually works
  (author-side check and maintainer-side PR review are the same skill).
- `.agents/skills/pr/` — use when creating a PR.

Harnesses that need their own directory (e.g. `.claude/skills/`) symlink into
`.agents/skills/` — that is the single source of truth.

## Hard rules

- Zero dollars, no payment verification with any vendor (ADR 0002/0004).
- Secrets live on the VMs or in GitHub Actions secrets — never in this repo
  (ADR 0004).
- Never point DNS at the VM IP; use the gateway hostname or tunnel CNAME.
