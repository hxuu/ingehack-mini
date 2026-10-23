# Inge MiniCTF — infrastructure status

Date: 2026-10-22. Platform: rCTF v2 (otter-sec/rctf, `ghcr.io/otter-sec/rctf:main`).

## OpenScaler VMs (region alg1, VPC 10.0.47.0/24, shared public IP 105.98.65.136)

| VM | ID | Size | Private IP | SSH |
|---|---|---|---|---|
| inge-minictf-challs | `01a1658c-bc46-7c00-9770-2707adfadf1a` | b-8-16-320 (8 vCPU / 16 GB) | 10.0.47.2 | `ssh minictf-challs` (public port 9305) |
| inge-minictf-platform | `01a1658d-01d1-7080-a04f-b74b0c8eaa82` | b-2-4-100 (2 vCPU / 4 GB) | 10.0.47.5 | `ssh minictf-platform` (public port 9379) |

- Quota: 10 vCPU / 28 GB is fully consumed (8 + 2). **No staging VM possible** until
  something is deleted. Staging was optional; redeploy instead.
- SSH user root, key `~/.ssh/id_edvps`.

## Port mappings (gateway 105.98.65.136)

| vm | internal | public |
|---|---|---|
| platform | 9479 (rCTF web) | 9383 → http://105.98.65.136:9383 |
| challs | 80 (Traefik http) | 9489 |

Note: public ports are auto-assigned by OpenScaler, so bookmark them via
`osctl computer network port list --computer <id>`.

## Platform VM (/opt/rctf, docker compose: rctf + postgres:18 + redis:8.2)

- Secrets in `/opt/rctf/.env`: `RCTF_DATABASE_PASSWORD`, `RCTF_REDIS_PASSWORD`,
  plus `RCTF_DATABASE_URL` / `RCTF_REDIS_URL` / `RCTF_DATABASE_MIGRATE=before`.
- rctf.d/: `01-ui.yaml` (name/home), `02-ctf.yaml` (origin/times/divisions/tokenKey),
  `04-instancer.yaml` (docker instancer → `http://10.0.47.2:12237` + shared token).
- Gotcha: `database:` block in YAML silently clobbers the connection with env-var
  merges; keep DB config in `.env` only (`RCTF_DATABASE_URL` string form works).
- Gotcha: quitting the installer prompt fails over ssh (`/dev/tty`); just run
  `docker compose up -d --force-recreate` manually.
- Recreate after config changes: `cd /opt/rctf && docker compose up -d --force-recreate`.
- Admin bootstrap: `POST /api/v2/auth/register` → `rctf user promote admin@ingeniums.club`
  (register confirmed: `rootadmin`, admin@ingeniums.club).
- Admin auth token is in the 2026-10-22 session history; rotate via new register + promote.

## Challenge VM (/opt/rctf-src, deploy/docker-instancer compose: traefik + redis + tiny-instancer)

- `.env` next to compose: `AUTH_TOKEN` (same as platform `04-instancer.yaml`),
  `INSTANCES_HOST=105.98.65.136.nip.io` (temporary until DNS; switch to
  `challs.ingeniums.club` later), `REDIS_PASSWORD`.
- compose.yml edits vs upstream: instancer port bound globally (`12237:1337`),
  `rctf_network` set `external: false` (split host).
- `/etc/docker/daemon.json`: default-address-pools 100.64.0.0/10 size 24.
- TLS: self-signed wildcard `*.105.98.65.136.nip.io` in `certs/` — replace with a
  Cloudflare DNS-01 Let's Encrypt cert for `*.challs.ingeniums.club` at DNS time.
- Firewall: `12237` must only be reachable from 10.0.47.5 (nothing else opens it;
  revisit with ufw at DNS time).

## Verified end-to-end (2026-10-22)

1. Platform web + API up: `/api/v1/challs` 200, auth guards 401, public 200.
2. Instancer schema served by rCTF (`/api/v2/admin/instancer/schema`).
3. Test challenge `hello-instancer` created (PUT /api/v2/admin/challs/...).
4. Admin-started instance ran on challs VM; served at
   `hello-<uid>.105.98.65.136.nip.io` through mapped port 9489. whoami responded.

## DNS + TLS cutover (2026-10-23, verified)

- Platform: CF Tunnel (token-managed), `ctf.ingeniums.club` orange → `localhost:9479`.
  `02-ctf.yaml`: `origin: https://ctf.ingeniums.club`, `proxy.cloudflare: true`,
  `proxy.trust: 1`. Cloudflared runs as a systemd service on platform.
- Challs: grey cloud. `*.challs` CNAME → `app.alpha.openscaler.net` (gateway;
  IP churn-proof). Mapped ports: 80→9489, 443→9471, 1337→9464.
- Cert: Let's Encrypt wildcard `*.challs.ingeniums.club` (+ apex) via certbot
  DNS-01 (`--cert-name challs-wildcard`, creds `/root/.secrets/cloudflare.ini`,
  zone-scoped Zone:DNS:Edit token — no payment info disclosed). Renewal deploy
  hook `/etc/letsencrypt/renewal-hooks/deploy/restart-traefik.sh` copies certs +
  restarts Traefik; `certbot renew --dry-run` passed. Expires 2027-01-21.
- `INSTANCES_HOST=challs.ingeniums.club` (nip.io retired). Gotcha: `docker compose
  restart` does NOT re-read .env — use `up -d --force-recreate`.
- Verified: `https://hello-<uid>.challs.ingeniums.club:9471/` serves the LE cert
  (openssl verify 0, wildcard match); plain-80 path works too (port 9489).
- WAF caveat: no CF proxy on challs — no edge WAF/rate-limit for challenge traffic.
- Known flaky: platform mapped port 9383 intermittently down — the tunnel
  (`https://ctf.ingeniums.club`) is the primary path.
- Zero-dollar constraint honored: no ACM/Total TLS, no card/PayPal anywhere.

## Pending (next session)

1. Set real event `startTime`/`endTime` before the event (currently now+48h test window).
2. Write-up bonus: check rCTF providers for a write-up/bonus mechanism or add a Misc
   workflow; verify scoring provider details (dynamic decay).

## Attachments wiring (2026-10-23, verified)

- `uploads/r2` live: `RCTF_UPLOAD_PROVIDER` + `RCTF_R2_*` env vars in
  `/opt/rctf/.env`, `publicBaseUrl=https://attachments.ingeniums.club`.
  R2 API token: Object Read&Write, scoped to the bucket, only in `.env`.
- Verified full round-trip: admin upload (`POST /api/v2/admin/upload`, field
  name `files`) → public fetch on the bucket CDN → `upload/query` lookup →
  attached to challenge (v2 PUT `files[]` entries require `size`) → detached.
- Note: challenge `files[].size` (bytes) is required by the v2 update route.
