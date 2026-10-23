# R2 for attachments despite the zero-dollar constraint

rCTF's default `uploads/local` provider is genuinely adequate for a miniCTF
(small footprint, one file server). We still switched the Platform to
`uploads/r2` because the maintainer's Cloudflare account already had an
active R2 subscription (created before the zero-dollar constraint was
articulated), and the already-built `attachments.ingeniums.club` custom domain
gets free, orange-served, unlimited-egress delivery of challenge files.
The R2 API token is Object Read & Write scoped to the single bucket.

## Status

accepted (2026-10-23)

## Consequences

- Attachments live on Cloudflare, keyed by SHA-256, served immutable
  (`max-age=31536000`) — so file URLs never change once uploaded.
- The rCTF v2 update route requires a `size` field on each `files[]` entry;
  challenge packaging scripts must include it.
- Backup strategy: platform DB via `pg_dump`, attachments are in R2 (vendor
  side; export a copy if the event's artifact record matters long-term).
- If the R2 subscription is ever cancelled, switch to `uploads/local` —
  the local provider is the documented fallback and is already the shape of
  the compose volume (`/opt/rctf/.data/uploads`), so no path changes.
