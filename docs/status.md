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

1. Set real event `startTime`/`endTime` before the event (currently a test window: now+48h).
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

## Verification record — 2026-10-23 E2E playthrough round (agent session 2)

Brand: working brand is now **Ingehack Mini** (`ctfName` runtime override set;
`flagFormatPlaceholder: 'ingehack{[\x20-\x7e]+}'` added to `/opt/rctf/rctf.d/01-ui.yaml`,
applied via `docker compose up -d --force-recreate`; homeContent still says
"Inge MiniCTF" — needs the same edit when homepage copy is finalized).

### hello-instancer E2E (all player-flow, verified this round)

- Fresh admin `qa-admin-471@ingeniums.club` registered + promoted to perms=63
  (rotate-by-fresh-email works). QA player teams 471/472/473 + 5 QA-RateLimit-*
  also exist; delete before the real event.
- Player instance routes verified: `PUT/GET/PATCH/DELETE` on
  `/api/v2/integrations/challs/hello-instancer/instance` (PUT/PATCH need `-d '{}'`).
  Extend ✓, stop ✓, restart after stop ✓.
- Solve flow: `POST /api/v1/challs/hello-instancer/submit` (v1 only) —
  wrong flag → `badFlag`, correct → `goodFlag` + solve recorded; later submit →
  `badAlreadySolvedChallenge`.
- Per-team flags now REAL: challenge switched to
  `flags/dynamic` (`flags/static` before) with base
  `ingehack{this_base_has_plenty_lowercase_letters_for_leet}`, mode auto → leet.
  Three concurrent instances served three distinct per-team flags inside
  `RCTF_FLAG` env (verified via `docker inspect` on Chall VM). `${RCTF_FLAG}`
  = first configured flag entry's concrete per-team value (docker-instancer docs).
- 3 concurrent instances ✓ isolated (per-flag + per-hostnamesuffix containers).

### Defects / pending work recorded from this round

1. **BLOCKER (UX): exposed endpoint advertises port 80** — rCTF reports
   `{kind:http, host: hello-<uid>.challs…, port:80}` but the gateway maps 80 →
   public 9489. `hello-<uid>.challs…:80` 503s; the *reachable* URL is
   `…:9489`. Same shape expected for https (443→9471) and tcp-ssl (1337→9464).
   Fix options: make the tiny-instancer/Traefik labels advertise the public
   port, or a maintainer-side rewrite in `04-instancer.yaml`, or document a
   "mapped port" note in the challenge UI copy until patched. NOT yet fixed.
2. `flagFormatPlaceholder` is config-file-only — runtime settings PUT ignores it.
3. **No captcha / IP throttle on registration**: 5 rapid registrations from one
   IP all 200 (`badBody` shape is fine). IP attribution is correct in rctf logs
   (`"ip":"105.235.138.234"`, real client via CF headers). Event-day spam/flag
   brute-force protection still needs CF Turnstile on register/instancer actions
   (rCTF captcha provider, free) — pending.
4. Admin instance-status GET for team 472 returned `stopped` while its container
   was running (observed once during QA cleanup; possibly keyed by instance-owner
   id ≠ our user id). Low priority; verify again with a clean repro.
5. Container `whoami` image cannot *show* the env flag — fine for instancer
   verification, useless as a player-facing hello challenge. The real
   `hello-instancer` delivering the flag visibly + correct/incorrect responses
   is to be authored via the new `new-challenge` skill.

## Update — endpoint-port blocker RESOLVED (2026-10-23, later same day)

Root cause & correct architecture (learned the hard way):
- The OpenScaler mapping is **public port → internal port**; the gateway dials
  the VM on the *internal* port. Traefik must keep listening on
  **80 / 443 / 1337** (socket, host+container).
- The mapped **public** numbers belong ONLY in what tiny-instancer *advertises*
  to players/challenges (`TRAEFIK_HTTP_PORT`/`HTTPS`/`TCP` in its `.env` —
  `KIND_TO_PORT` is advertisement-only).
- Consequence: mapped ports rotated during the session. Current mapping:
  challs **80→9487, 443→9488, 1337→9450** (osctl list confirmed; platform 9479→9383
  unchanged). `compose.yml` published ports left at the stock 80:80/443:443/
  1337:1337; `conf/traefik.yml` entrypoints :80/:443/:1337 (stock).
- Verified end-to-end after fix: rCTF advertises `port:9487` and
  `http://hello-<uid>.challs.ingeniums.club:9487/` serves the instance from
  the local machine. QA instance stopped and removed afterwards.
- osctl notes: `port open <internal>` assigns public automatically; closing and
  re-opening re-assigns (rotates) numbers. A reboot did NOT change the numbers.
- update-mapped-ports routine: run `osctl computer network port list --computer
  <challs-id>`, then set TRAEFIK_HTTP_PORT/HTTPS_PORT/TCP_PORT in
  `/opt/rctf-src/deploy/docker-instancer/.env` to the PUBLIC numbers, then
  `docker compose -f deploy/docker-instancer/compose.yml up -d --force-recreate`.
  No editor/player action needed; instance URLs advertise the current numbers.

## Load test — 2026-10-23, staged through the real CF edge/tunnel (client: local aiohttp script /tmp/opencode/loadtest.py, monitor: /tmp/loadmon*.log on platform)

| Stage | Shape | Result |
|---|---|---|
| 1 reads | 250 "users" polling `/`, `/api/v2/challs`, `/api/v2/leaderboard` (= ~800 rps at one-client pacing) | PASS: p95 168 ms, p50 69 ms, zero 5xx over 72k requests; platform load ≤2.5, rctf container ≤49% of one core, Postgres quiet (fast path is cached/rateless) |
| 2 submits | 120 workers hammering `POST /api/v1/challs/:id/submit` bad flags | PASS (defensively): rCTF rate-limits submissions (15,140×429, 13×400, no 200s) — brute-forcing flags from one IP is throttled without touching the DB |
| 3 onboarding | 40 workers × rapid registration + every 6th starting an instance | PASS: p95 352 ms, worst outlier 5.4 s (first-instance Traefik spin-up), zero 5xx; **BUT** it spawned ~95 concurrent QA instances on Chall VM → its load spiked to 8.7 then recovered after cleanup |

Verdict for 200–250 real players: platform (2 vCPU/4 GB) has comfortable
headroom — real players word-choice at ~1–3 rps each = ≤750 rps worst-case,
stage 1 proved 800 rps fine with p95 <200 ms. Load is bounded by the submit
rate-limit and instancer start cost, not the read path.

Operational notes / follow-ups:
- Pre-event DB cleanup: delete all `QA-*` + `LoadTest-*` users (dozens of test
  teams now exist), then tear down any stray instances (docker: `ti-hello-…`).
- Instancer start is the expensive path (Redis CPU spike + platform 2.4 s
  outliers). CF Turnstile on `instancerStart`/`instancerExtend` (already
  pending) also caps launch storms at event start.
- `/api/v2/leaderboard` returned `badEndpoint` (404) — my script guessed a
  wrong path; scoreboard route may be v1 or differently named. Check the real
  UI route once before event day (cheap).
- Chall VM load spike during mass-spawn is expected; real event has each team
  spawning at most once per challenge per 30 min, spread over minutes.

## Registration kill switch — verified 2026-10-23 (role-matrix row 4)

- `registrationsEnabled` / `flagFormatPlaceholder` are **config-file only**;
  the admin settings PUT silently ignores them (PUT succeeded but had no
  effect, and client config kept `true`).
- Event-day freeze routine:
  `printf "registrationsEnabled: false\n" > /opt/rctf/rctf.d/03-frozen.yaml
   && cd /opt/rctf && docker compose up -d --force-recreate rctf`
  then `GET /api/v2/integrations/client/config` must show `false` and register
  returns `badRegistrationsDisabled`. Re-enable = delete the file +
  force-recreate. KEEP 03-frozen.yaml out of the rctf.d dir between events.

## CI/CD pipeline — LIVE-verified 2026-10-23 (ADR 0005)

- Repo is live at https://github.com/hxuu/inge-minictf (private).
- Bot admin `ci-bot@ingeniums.club` (+ register fresh token, perms
  **challsRead|challsWrite = 3 only**), token stored as GitHub Actions secret
  `CHALLENGE_BOT_TOKEN` (repo-scoped; rotate = re-promote fresh email + one
  `gh secret set`).
- `ops/register-challenge.sh` rewritten to the verified v2 schema
  (`docs/research/rctf-v2-api-schema.md`): correct payload (`points`,
  `flags[]` entries, `{data:{...}}` wrapper, `instancerConfig` inside
  `challengeIntegrationId`), validates the instancer `config` against the
  LIVE `GET /api/v2/admin/instancer/schema` JSON Schema pre-PUT, and upserts
  via one `PUT /api/v2/admin/challs/:id` (create-when-missing semantics — no
  branching). LIVE-verified end-to-end: registered QA challenge
  `qa-pipeline-chall` via the bot (then re-confirmed update path).
- Bot boundary checks (role matrix row 3 = partial perms editor, also
  verified): settings PUT → `badPerms` ✓, user delete → `badPerms` ✓,
  challenge PUT → success ✓ (leaked bot token cannot touch event config).
- Registration kill switch verified (row 4, see the dedicated section).
- Workflow `.github/workflows/challenges.yml` triggers on merged changes
  under `challenges/**` (detect matrix → docker build → public GHCR push →
  register via bot). First REAL-MERGE round-trip (PR → GHCR image pull at
  instance start on the Chall VM) is the remaining integration test, owed
  when the first authored challenge ships.
- Local-handout uploads via the admin `POST /api/v2/admin/upload` are bot-
  capable but NOT yet wired (script explicitly refuses local-handout challs
  instead of half-registering). Wire-in owed.

## Author pair live — 2026-10-23 (first full author round-trip, repo renamed)

- Repo renamed: **https://github.com/hxuu/ingehack-mini** (was inge-minictf).
- Author flow executed as designed (PR #1 via `new-challenge` scaffold →
  `challenge-review` verify ladder → merge): challenges ship via CI
  automatically, authors have NO ssh key/VM access — the deploy key lives only
  in the repo's Actions secrets (`SSH_DEPLOY_PRIVATE_KEY`), used by CI post-
  merge. Repeated a couple of CI fixes on the way:
  1. workflow YAML name with colon didn't parse (actionlint now used before
     every workflow edit — keep it).
  2. GHCR push via GITHUB_TOKEN denied → **pipeline switched to registry-less
     CI**: runner builds → `docker save | ssh docker load` on the challs VM →
     instanced challenges registered with a LOCAL image tag (`name:<sha>`,
     no registry pull needed at instance start); static challenges deployed
     as labeled containers behind the challs Traefik with the flag from
     chall.yaml injected via env. Challenge images never leave the VM.
  3. register script now validates the RESOLVED payload config (before it
     validated the raw manifest — missing required `image`).
- Live verification results:
  - `challenges/misc/hello` (static): deployed, serves page + `/flag` with the
    declared flag `ingehack{http_is_just_requests}` at
    `hello.challs.ingeniums.club:9487` (traefik web entrypoint).
  - `challenges/misc/hello-instancer`: CI-registered via the inscriberbot PUT
    (image `hello-instancer:<sha>` local, flags unchanged, 3 exposes). Player
    start (as QA-Player) → instance from the CI-shipped image on the VM,
    THREE expose kinds verified live with the per-team leet flag:
    http `hello-http-<uid>…:9487`, https `hello-https-<uid>…:9488`,
    tcp-ssl `hello-tcp-<uid>…:9450` (curl note: the tcp-ssl kind responds over
    HTTP/1.1; use `curl --http1.1` when scripting TLS test hits — browsers/pwn
    clients unaffected).
- QA instance started/stopped during verification. Challenge pairing on the
  platform now: hello (static) + hello-instancer (3-expose instanced) + the
  QA pipeline challenge `qa-pipeline-chall` (DELETE before event).
