# inge-minictf

Infra repo for **Inge MiniCTF** — a 48-hour jeopardy CTF for first-year CS
students at ingeniums.club, running on rCTF v2 across two OpenScaler VMs
behind Cloudflare.

Read in this order:

| Document | What it gives you |
|---|---|
| [GLOSSARY.md](./GLOSSARY.md) | The domain language (Platform, Challenge Instance, Mapped Port, …). Read this first — the rest uses these words. |
| [docs/adr/](./docs/adr/) | Why the topology is the way it is (tunnel vs grey cloud, split hosts, R2, secrets discipline). The no's are as important as the yes's. |
| [docs/status.md](./docs/status.md) | Live state: VM IDs, mapped ports, file locations, gotchas, verification records. |
| [docs/research/rctf-certs-and-zero-dollar-tls.md](./docs/research/rctf-certs-and-zero-dollar-tls.md) | Primary-source backing for every TLS/cert claim in the ADRs. |

Quick sanity checklist for a new maintainer:

1. `ssh minictf-platform` / `ssh minictf-challs` (root, `~/.ssh/id_edvps`).
2. Platform health: `curl -s https://ctf.ingeniums.club/api/v1/challs` — expect `goodChallenges`.
3. Config changes: edit `/opt/rctf/rctf.d/*.yaml` (or `.env` for secrets),
   then `cd /opt/rctf && docker compose up -d --force-recreate`.
4. Instancer changes: edit the `.env`/compose in
   `/opt/rctf-src/deploy/docker-instancer` on the Challenge VM, then
   `docker compose up -d --force-recreate` (restart alone does NOT re-read `.env`).
5. DNS: CNAMEs point at the gateway hostname, never at the IP.
6. Hard constraint: zero dollars spent, no payment verification disclosed to
   any vendor. If a proposed change requires card/Mastercard verification, it
   needs a new ADR superseding `0002`.
