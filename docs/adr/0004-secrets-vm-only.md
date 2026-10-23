# Secrets live on the VMs, never in git

Every secret in this deployment (rCTF tokenKey, DB/Redis passwords, instancer
auth token, Cloudflare API tokens, R2 keys) lives in files on the machines
that use it — `/opt/rctf/.env`, the instancer `.env`,
`/root/.secrets/cloudflare.ini` — and only those files. The repo carries
pointers to locations, never values. This is the AlphaCTF discipline carried
over (`/tmp` wipes, the `password`/`base64` URL-encoding pitfalls), tightened
by the fact that this repo may someday go public and secrets in git are
unfixable in CTF timelines.

## Status

accepted (2026-10-22)

## Consequences

- Losing a VM means re-deriving its `.env` from the password manager (the
  operator keeps a copy of the tile values), not from this repo.
- Cloudflare tokens are all zone- or bucket-scoped by least privilege:
  Zone:DNS:Edit for certbot (renewal), tunnel token for the Platform tunnel,
  Object Read&Write (bucket-scoped) for rCTF uploads. Blast radius is bounded
  per token; rotate by editing the on-VM file and recreating the affected
  service.
