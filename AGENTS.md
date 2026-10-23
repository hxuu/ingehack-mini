# Ingehack Mini — maintainer & agent instructions

Ingehack Mini is a 2-VM beginner CTF (platform VM runs rCTF v2; challenge VM runs
the rCTF v2 Docker instancer). Infra is built and documented — see
`docs/status.md` (source of truth for live state), `GLOSSARY.md` (domain
language), `docs/adr/` (why the topology is what it is).

## Skills in this repo

Two skills ship inside this repo; any agent harness launched from within a clone
of it can use them:

- `.agents/skills/new-challenge/` — scaffold, update, or ship a challenge
  (the only skill a challenge author needs).
- `.agents/skills/challenge-review/` — verify a challenge actually works
  (author-side check and maintainer-side PR review are the same skill).

Harnesses that need their own directory (e.g. `.claude/skills/`) use symlinks
into `.agents/skills/` — the single source of truth is always `.agents/skills/`.

## Hard rules

- Zero dollars, no payment verification with any vendor (ADR 0002/0004).
- Secrets live on the VMs or in GitHub Actions secrets — never in this repo
  (ADR 0004).
- Never point DNS at the VM IP; use the gateway hostname or tunnel CNAME.
- Challenge authoring body of work: `challenges/<category>/<name>/`. Read
  `new-challenge` before creating or editing anything there.