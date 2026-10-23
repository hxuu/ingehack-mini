# rCTF v2 as the platform, split across two VMs

The handoff mandates rCTF v2 (otter-sec/rctf) with its native Docker instancer.
We deployed it split-host: Platform (rCTF + Postgres + Redis, 2 vCPU / 4 GB) on
one VM, Docker instancer + Traefik (8 vCPU / 16 GB) on another. The Challenge
VM deliberately gets the more resource-rich machine — instances stack up
there; the Platform only serves web/API/DB and never runs challenge workloads.
OpenScaler's account quota (10 vCPU / 28 GB) is the binding constraint, which
is also why there is no Staging VM right now.

## Status

accepted (2026-10-22)

## Consequences

- The instancer is reachable from the Platform over the private network only:
  the instancer API binds `12237:1337` globally on the Challenge VM, and the
  Platform container talks to `http://10.0.47.2:12237` with a shared token.
- `rctf_network` is declared `external: false` in the instancer compose
  (upstream assumes same-host) — this deviation is intentional, not a bug.
- Secrets live only on the VMs (`/opt/rctf/.env` on Platform, instancer `.env`
  on Challenge VM, `/root/.secrets/cloudflare.ini` for certbot). Never in git.
- Platform config lives in `/opt/rctf/rctf.d/*.yaml`; DB connection strings
  specifically live in `.env` (env), NOT in rctf.d — rCTF's env-var merge
  clobbers a YAML `database:` block and breaks boot.
