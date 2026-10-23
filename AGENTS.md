# Ingehack Mini — agent instructions

Platform docs: `docs/status.md` (live state), `GLOSSARY.md` (domain
language), `docs/adr/` (topology rationale).

## Skills in this repo

Inside this repo: challenge lifecycle skills live in `.agents/skills/` —
`new-challenge` (read before creating or editing anything under
`challenges/`), `update-challenge` (change a live challenge),
`remove-challenge` (retire one), `challenge-review` (verify a challenge
actually works — author-side check and PR review are the same skill), and
`pr` (use when creating a PR).

Harnesses that need their own directory (e.g. `.claude/skills/`) symlink into
`.agents/skills/` — that is the single source of truth.

## Hard rules

- Zero dollars, no payment verification with any vendor (ADR 0002/0004).
- Secrets live on the VMs or in GitHub Actions secrets — never in this repo
  (ADR 0004).
- Never point DNS at the VM IP; use the gateway hostname or tunnel CNAME.
