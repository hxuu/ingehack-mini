# Inge MiniCTF — infrastructure status

Date: 2026-10-23. Platform: rCTF v2 (otter-sec/rctf, `ghcr.io/otter-sec/rctf:main`).

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
- Pre-event DB cleanup: DONE 2026-10-23 (see the Pre-event cleanup round).
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

## Player-UX round — URL display + shared-instance wired (2026-10-23, verified)

- **Root cause of "no instance URL"**: rCTF's `filterInstanceEndpoints`
  drops every endpoint whose stored `expose` entry lacks a truthy
  `shouldDisplay` — and in rCTF's schema `shouldDisplay` is optional with NO
  default (the docs example `true` is only an example, not a default). Our
  manifests omitted it → players got `endpoints: []` while instances ran fine.
  Fix: `ops/chall-payload.py` now defaults `shouldDisplay: true` per expose
  (opt out per entry), manifests write it explicitly. Verified: player
  GET instance returns all three URLs with titles
  (`hello-http-<uid>…:9487`, `hello-https-…:9488`, `hello-tcp-…:9450`).
- **Hello renamed**: `challenges/misc/hello` → `sanity-check` (same static
  flag/page flavor). Never registered before the rename, so no stale id.
- **New `hello-shared`**: static shared-instance exemplar — one server for
  everyone, a shared visit counter on `/`, the flag in the `X-Flag` response
  header on `/flag` (teaches header inspection). HEAD probes 501 →
  `do_HEAD = do_GET` alias; solver note says `curl -si`, not `-sI`.
- **CI now registers static challenges on the platform** (workflow: register
  step runs for `instanced: false` too — payload has no `instancerConfig`,
  `--image` is a log label only). Before this, static challenges were deployed
  behind Traefik but invisible on the platform entirely.
- Player-flow verification (fresh QA token): challenge list shows
  `sanity-check`, `hello-shared`, `hello-instancer` (+ QA challenge);
  instance start→running→endpoints; `/flag` on the instance serves the
  per-team leet flag (`ingehack{7H15_B453_h45_pl3N7y_10W3Rca5e_l3t73Rs_f0r_133t}`);
  wrong submit → `badFlag`, correct submit → `goodFlag` + solve recorded.

## Static raw-TCP exposure (2026-10-30, verified)

- `ops/deploy-static.sh` gained a `tcpPort:` branch: a static challenge whose
  manifest sets `tcpPort: <container port>` gets a Traefik **TCP** router on
  the `tcp` entrypoint (1337 → public 9450), `HostSNI(<name>.challs…)`, TLS
  terminated by the wildcard cert. No new mapped port, no VM change; static
  HTTP challenges take the unchanged `web`/`websecure` path.
- `sudoers` (`challenges/linux/sudoers`, author boul3h14) is the first user:
  sshd on container port 22, reached at `sudoers.challs.ingeniums.club:9450`
  with `ssh -o ProxyCommand='openssl s_client -quiet -servername %h -connect
  %h:%p' ctf@sudoers.challs.ingeniums.club -p 9450` (password `ctf`).
- Verified live on the CI-deployed container: SSH banner
  `SSH-2.0-OpenSSH_8.9p1`, password auth, and the solver's payload
  (`dlopen` plugin calling `seteuid(0)`) returns
  `ingehack{seteuid_leaves_suid_restorable}`.

## Pre-event cleanup round (2026-10-23, done)

- **Users swept: 4,068 → 4.** Deleted all `loadtest-*` (4,048 bulk copies from
  the load-test runs), `qa-player/ratelimit/urltest/attach-admin-fixture`, and
  `test-player/test-admin/frozen*` accounts. Kept: `admin@` (rootadmin),
  `ci-bot` (the CI identity), `Team authors` (ladis30704@hopefunder.com), and
  `qa-attach-…` — the last promoted to the manual admin token
  (`/tmp/opencode/qa-admin-token`); the other QA admins could not be
  API-deleted while privileged, so they were first demoted via the CLI on the
  platform VM (`docker exec rctf-rctf-1 rctf user demote <email>`) and then
  deleted normally. Route: `DELETE /api/v2/admin/users/:id`; paginated listing
  needs `?limit=100&offset=N` (bare or partial params → `query:offset:
  Invalid input`).
- **`qa-pipeline-chall` wiped** off the platform (hidden, then v1-deleted):
  the player-visible challenge list is exactly the five sanity checks.

## CI lifecycle round (2026-10-23, proven live)

The `challenges` workflow now covers create, update, AND delete on a merged
PR — until this round it only handled create/update (a deleted directory
silently did nothing on the platform).

- **Delete path**: new `retire` job. `detect` additionally lists dirs fully
  deleted at HEAD (diff-filter=D + absence check, so a pruned file inside a
  live dir stays an update). `retire` recovers the old `chall.yaml` from
  `git show HEAD^:`, derives the id with the SAME python expression as
  `register-challenge.sh` (instancer-level `challengeIntegrationId` →
  top-level → `name` slug), then `ops/remove-challenge.sh --wipe` + ssh
  `docker rm -f static-<dirname>` (gated on `instanced != true`).
- **Proven end-to-end** with the scratch `ci-lifecycle-test` (static, no
  handcrafted code): merge #1 registered + deployed it (200 on
  `:9487`, `X-Flag` header), merge #2 deleted the dir → `retire`
  hidden+wiped the entry and removed the container; platform list and
  Traefik host both clean afterwards.
- Two workflow-file bugs caught by GH's parser in the process (each reject
  killed the run in 0s with "workflow file issue"): `env:` may NOT sit
  inside `strategy:`, and `matrix:` must sit inside it (run 40004352378,
  40004556472).
- **Ship job latent bug found by the fixture**: a static manifest with NO
  `instanced:` line left the `chall` step's output empty, and the register
  steps gate on `== 'false'` — registration silently skipped. Now default
  `instanced=false` on absence (same rule the retire job reads with).
- Node: only pushes touching `challenges/**` fire runs at all — workflow-only
  commits neither self-test nor self-heal; a parse error surfaces on the next
  challenge push.

## Naming + URL-scheme round (2026-10-23, verified)

- All sanity challenges now brand as the **sanity-check series**:
  display names `sanity-check`, `sanity-check-shared` (was hello-shared),
  `sanity-check-instanced` (was hello-instancer, id unchanged — instanced
  challenges pin `challengeIntegrationId` so solves survive the rename),
  `sanity-check-2`/-3.
- **Static-challenge renaming gotcha**: with no `challengeIntegrationId`, a
  static challenge's id derives from its `name` — renaming the display name
  creates a NEW id. Old `hello-shared` was hidden + wiped via
  `ops/remove-challenge.sh`; its directory keeps the name so the
  `hello-shared.challs…` Traefik host label is unchanged.
- **The 404 mystery was a scheme/port mismatch**: hitting
  `https://…:9487` (https scheme on the plain-HTTP entrypoint) makes Traefik
  return "404 page not found". Descriptions now say
  `http://…:9487` or `https://…:9488` explicitly — scheme follows the port.
  Additionally `deploy-static.sh` only declared the `web` entrypoint, so
  https on static challenge hosts did not exist; it now declares BOTH
  (web + websecure/tls routers sharing one service). Verified: all four
  static hosts answer 200 on http://9487 and https://9488 with the
  `*.challs.ingeniums.club` LE wildcard cert.
- **`remove-challenge.sh` had two latent bugs, found on its first live run**:
  (1) admin GET kind is `goodAdminChallengeV2`, not `goodChallengeV2`;
  (2) the hide-PUT must be `{data: {...}}` containing only writable fields —
  round-tripping the raw admin-GET entity (with `id`/`solveCount` and
  `sortWeight: null`) returns `badBody`. It now strips read-only fields and
  drops null values (`sortWeight` rejects explicit null).

## Attachments sanity checks — `sanity-check-2`/-3; upload wiring PROVEN (2026-10-23)

- **`register-challenge.sh` now uploads local handouts** (multipart
  `POST /api/v2/admin/upload`, field name `files`) and attaches every handout
  as `{name, url, size}` — the owed wire-in from the CI round. Dedup is by
  SHA-256, so CI re-registering an unchanged file returns the same url.
  `chall-payload.py` passes `files[].path` through to the register script,
  which resolves it against the manifest dir and auto-fills `size` from the
  file when the manifest omits it.
- **`sanity-check-2`** — local-attachment path: `files/naughty-list.zip`
  committed to the repo, flag on the first line inside
  (`ingehack{naughty_but_readable}`). **`sanity-check-3`** — R2 path:
  `gifts.zip` uploaded to the bucket by hand (admin upload), chall.yaml
  references its `attachments.ingeniums.club` URL (`ingehack{bucket_list_
  checked_twice}`); the `url`-entry form requires the real `size` in the
  manifest.
- Both verified player-side (fresh QA token): attachment visible in
  `GET /api/v2/challs` `files[]`, public download 200 from
  attachments.ingeniums.club (no auth), wrong submit → `badFlag`,
  correct submit → `goodFlag`; CI re-register via the bot token worked
  identically (perms 3 is enough for upload).
- QA admin used for the R2 seed upload: `qa-attach-1792778575@ingeniums.club`
  (perms 63) — KEPT as the manual admin token (`/tmp/opencode/qa-admin-token`),
  uniquely deletable via the CLI-demote path if rotation is ever wanted.

## Updating challenge metadata without a rebuild (added when needed)

Merged-PR CI always rebuilds + ships the image; a pure manifest-text fix
(description, points, tags, `releaseTime`, expose layout) does not need that.
`ops/update-challenge.sh --platform ... --manifest <chall.yaml> --token ...`
re-registers from the manifest directly. Image handling in an instanced
payload: with no `--image` the script reuses the LIVE service images (GET /
api/v2/admin/challs/:id) — i.e. whatever CI shipped last; adding/removing a
service with no live counterpart requires `--image`. The payload builder is
shared with register in `ops/chall-payload.py` — the manifest contract lives
there once. Code/Dockerfile changes still go through CI (ADR 0005).

## Removing a challenge from the platform (added when needed)

rCTF v2 has no v2 challenge-delete route; the only hard delete is the v1
`DELETE /api/v1/admin/challs/:id`. Clean removal procedure
(`ops/remove-challenge.sh`, same bot-token auth as register):

1. **Hide (always)**: script PUTs the live challenge back with `hidden=true`
   (round-trips the GET payload; on rejection, fallback is `hidden: true` in
   `chall.yaml` + merge → CI re-registers hidden).
2. **Wipe (optional, `--wipe`)**: v1 delete. Script warns on failure and the
   challenge then stays hidden rather than deleted.
3. **Manual sweep (no API covers)**: delete the GHCR image from the org's
   package settings; per-team instances expire via `timeoutMilliseconds` (or
   `DELETE /api/v2/admin/challs/:id/instance` acting per admin team); merge the
   PR deleting `challenges/<category>/<name>/` so CI stops shipping it.
   Re-merging the old manifest would unhide/restore the challenge.
4. **Solves**: a hidden challenge keeps existing player solves — fine for a
    withdrawal. The perms-3 bot has no solve-write perms, so solve cleanup is
    a manual admin action (see schema docs §Users) if ever needed.

Usage:
    ops/remove-challenge.sh --platform https://ctf.ingeniums.club \
      --challenge-id <id> --token "$CHALLENGE_BOT_TOKEN" [--wipe]

## Platform lockdown before publish — 2026-10-24 (verified)

Working state while challenges are being authored and the event is unpublished.

- **Registration frozen**: `/opt/rctf/rctf.d/03-frozen.yaml` contains
  `registrationsEnabled: false`, applied with
  `docker compose up -d --force-recreate rctf`. Client config reads `false`;
  `POST /api/v2/auth/register` → `badRegistrationsDisabled`.
- **All eight challenges hidden** (`hidden: true` in every manifest under
  `challenges/`). On merge CI re-registers them hidden and anonymous
  `GET /api/v2/challs` returns 0 entries; admins still see everything via
  `GET /api/v2/admin/challs`. Every manifest carries the flag, so a CI
  re-registration cannot silently unhide a challenge.
- **Accounts cut to two**:
  - `Team authors` (perms **63**) — the shared authors credential. Sign-in is
    a **team token** pasted into the "Team token" field on `/login` (rCTF v2
    is passwordless; there is no password). The token is held off-repo on the
    maintainer machine, never in git.
  - `ci-bot` (perms **3**) — kept deliberately: the `challenges` workflow
    authenticates as it via the `CHALLENGE_BOT_TOKEN` Actions secret. Deleting
    it breaks CI until a new bot account is created and the secret rotated.
  - Deleted: `rootadmin`, `QA-Attach`, `boul3h14`, and the temporary cleanup
    admin. There is no separate root identity any more; `Team authors` is the
    only human admin.
- **Gotcha — hiding is undone by CI**: a merged PR touching a challenge
  directory re-registers it from `chall.yaml`, whose `hidden` defaults to
  `false`. PR #6 dropped `hidden: true` from the OSINT trio and CI
  re-registered them public; it is now explicit in all eight manifests. Any
  new challenge must set `hidden: true` until publish.
- **Visibility rules** (rCTF v2, `packages/types/src/routes/v2/challenges.ts`
  and `apps/api/src/services/challenge-queries.ts`):
  - `GET /api/v2/challs` is `onlyWhenStarted`: before `startTime` it returns
    `badNotStarted` to everyone except holders of `challsRead` (admins).
  - After `startTime` the list is anonymous and filtered only by each
    challenge's `hidden` and `releaseTime`; there is no login requirement.
  - So once the test window is open, `hidden: true` is the only lever that
    keeps challenges away from anonymous visitors — `startTime` alone stops
    working the moment the competition starts.
- **Unfreeze at publish**: delete `/opt/rctf/rctf.d/03-frozen.yaml`, then
  `docker compose up -d --force-recreate rctf`; unhide challenges (manifest or
  admin PUT) once the event is meant to be visible.

## Skin Release `ingehack-skin-v1` live on the Platform — 2026-11-01 (verified)

The Platform stopped running the stock rCTF image: it now runs a Skin Image
built from the private fork `hxuu/ingehack-skin` (ADR 0006).

- Release: git `b2e59e98` on branch `skin`, tag `ingehack-skin-v1`, based on
  `cf80517c` — the upstream commit the Platform was already running, so the
  release carries no upstream changes of its own. Image
  `ghcr.io/otter-sec/rctf:ingehack-skin-v1` (the tag inherits upstream's repo
  name from `compose.yml`; nothing is pulled from that registry). Local build id
  `sha256:091a44c2…`; the VM reports `sha256:ad054d17…` because the two daemons
  use different image stores — a per-file SHA-256 manifest of `/app` in both
  shows only `/etc/hostname`, `/etc/hosts`, `/etc/resolv.conf` differ, i.e.
  per-container runtime files, so the loaded image is the built one.
- Shipped registry-less: `docker save | ssh minictf-platform docker load`,
  tarball kept at `/opt/rctf/images/ingehack-skin-v1.tar.gz` (97 MB).
- Deployed by `RCTF_GIT_REF=ingehack-skin-v1` in `/opt/rctf/.env` (previous file
  kept as `.env.pre-skin-backup`) + `docker compose up -d --force-recreate rctf`.
  **Rollback**: `RCTF_GIT_REF=main` + force-recreate; the upstream image is still
  on the VM.
- **Skin-only, checked**: an image-vs-image file manifest (before `:main` vs
  after the release) differs in 427 files under `/app/static/**` and in **no**
  `/app` file outside it; the remaining 124 differences are Alpine base-image
  drift (`python3.12.14→3.12.16`, brotli, expat) and per-container `/etc` files.
  Anonymous API responses are byte-identical across the swap (`/api/v2/challs`,
  `/api/v1/challs`, client config, `/api/v1/leaderboard` 404, auth 401s,
  `robots.txt`); the root document differs only in its pre-paint script
  (`theme.js` → `ingehack/skin.js`).
- **Favicon** (`faviconUrl` left at the stock redpwn default in config): the skin
  now treats that default as unset, so the skin icons win; `/favicon.ico` serves
  the skin art (`sha256 e2d34693…`) on the live domain.
- Verified live on `https://ctf.ingeniums.club` in light and dark: skin namespace
  stamped, `data-ih`; rope flanks beside the lockup (brown `#8a5a2b` light /
  `#c79a63` dark, right-hand one mirrored); theme toggle flips and persists
  `ih-theme-mode` across reloads; no new console or CSP errors (the only one is
  the pre-existing Cloudflare Analytics beacon). Screenshots:
  `~/work/ingehack-skin/notes/live-shots/`; the manifests, before/after HTTP
  bodies and check scripts: `~/work/ingehack-skin/notes/skin-verify/`.
- Known gap: the timer block (and its clock) renders only where config content
  carries a `<timer>` tag. The live `homeContent` has none, and the test event
  window (2026-10-22 22:47 → 10-24 22:47) has ended, so the home page shows
  "CTF ended" and no clock. Adding `<timer />` to `homeContent` (and a real
  window) is an event-content decision, not a skin one.
- Next: extract the palette/art/wordmark behind one theme surface so a second
  event reuses the Skin; the skin repo's README records the procedure.

## Skin Release `ingehack-skin-v2` — edge-to-edge plate, live on the Platform (2026-11-01, verified)

The v1 skin left a bare band down the right edge of every page. Cause: rCTF's
own `layout.css` sets `scrollbar-gutter: stable`, reserving a ~15 px gutter even
on pages that do not scroll; the fixed ship plate and the header cannot paint
into that strip (only the flat page colour reaches it), so it showed as an empty
column. Fixed skin-side with `scrollbar-gutter: auto` on `html[data-ih]`, so the
gutter is reserved only when a scrollbar is actually needed.

- Release: git `6f800f58` on branch `skin`, tag `ingehack-skin-v2`, based on
  `ingehack-skin-v1`. Image `ghcr.io/otter-sec/rctf:ingehack-skin-v2`, shipped
  registry-less and kept at `/opt/rctf/images/ingehack-skin-v2.tar.gz`;
  deployed by `RCTF_GIT_REF=ingehack-skin-v2` + force-recreate. **Rollback**:
  `RCTF_GIT_REF=ingehack-skin-v1` (or `main`) + force-recreate; both older images
  remain on the VM.
- **Delta from v1, checked**: a per-file SHA-256 manifest of `/app` in both
  images differs in 120 files, all under `/app/static/_app/` (the content-hashed
  CSS bundle and the JS chunks whose hashes roll with it, plus `index.html` and
  `version.json`); no `/app` file outside `/app/static`.
- **Behavioural parity**: anonymous API bodies byte-identical across the swap
  (`/api/v2/challs`, `/api/v1/challs`, client config, auth 401s, `robots.txt`);
  only the root document changed.
- Verified live: `scrollbar-gutter` computed `auto`, the plate spans the full
  viewport width on a short page, no console or CSP errors. Evidence and
  before/after HTTP bodies: `~/work/ingehack-skin/notes/v2-verify/`.


## Platform accounts — `Hxuu` admin + view-only `authors` (2026-11-01, verified)

Current platform users (was `ci-bot` + a second full admin):

| user | email | perms | role |
|---|---|---|---|
| `Hxuu` | hxuu@ingeniums.club | 63 (all) | the sole full admin, owner's account |
| `authors` | authors@ingeniums.club | 1 (`challsRead`) | the authors team: can see every challenge (incl. hidden) on the participant UI and nothing else |
| `ci-bot` | ci-bot@ingeniums.club | 3 (`challsRead,challsWrite`) | CI identity only |
| `Team authors` | ladis30704@hopefunder.com | 0 | **demoted** from 63; kept, not deleted |

- **Registration is the only way to create a user.** `POST
  /api/v2/auth/register` returns `{authToken, teamToken}`; perms are then set
  with the container's CLI, `docker compose exec -T rctf rctf user promote
  <email> [--perms <names>]` (no domain is appended to a bare `<email>`).
  **`perms` is an option, not a second positional** — `promote <email>
  challsRead` silently grants ALL perms; use `--perms challsRead`.
  `demote <email>` zeroes perms. `create-user-token` and `updateAdminUser`
  both refuse a target with `perms > 0`, so a fresh account is registered
  first and promoted second.
- Creating a limited-perms account needs registration open, so the freeze was
  lifted for the two registrations and restored: `/opt/rctf/rctf.d/
  03-frozen.yaml` moved aside → `docker compose up -d --force-recreate rctf`
  (config reports `registrationsEnabled: true`) → register both → promote →
  move the file back → recreate. End state verified: `registrationsEnabled:
  false`, and a fresh register returns `badRegistrationsDisabled`.
- **Tokens**: the owner's pasted token (`WqS5k0DPIuj_…`) does not decrypt with
  the live `tokenKey` (`02-ctf.yaml`) — it was minted by a different install,
  so it can never authenticate against this platform. Working tokens
  were minted at registration. rCTF v2 tokens are stateless AES-GCM blobs keyed
  by `tokenKey`; the value lives in `02-ctf.yaml` and **rotating it invalidates
  every existing token at once**.
  - The browser login consumes the **`teamToken`**, via
    `https://ctf.ingeniums.club/login?token=<teamToken>` (the page shows "This
    link contains a team token. Click Login to confirm"). Both tokens were
    exercised live: login lands on `/` as `Hxuu` / `authors`, and both get the
    `/admin/challenges` link. `POST /api/v2/auth/verify {verifyToken:
    <teamToken>}` returns a fresh `authToken` if a script needs one.
  - A script consumes the **`authToken`** as `Authorization: Bearer …`; it is
    valid for the admin API and, because perms are read per request, keeps
    working after a later `promote`.
- Authorization boundary, checked with the `authors` token: `GET
  /api/v2/admin/challs` → 200 (all 8 challenges, hidden included); `GET
  /api/v2/admin/users?limit=5&offset=0` → 403 `badPerms` (`usersWrite` absent).
  `Hxuu` gets 200 on both.
- **No scoreboard leak**: `Hxuu` and `authors` are teams, but the public
  leaderboard only ranks users with a recorded solve (`global_rank` stays NULL
  otherwise), so privileged accounts with no solves do not appear.
- **Open**: the demoted `Team authors` (an old second admin) is kept rather
  than deleted — deleting it is a separate call (`DELETE
  /api/v2/admin/users/:id`, or first demote while privileged).

## Platform Patch `ingehack-author-preview-v1` — authors see hidden challenges as players do (2026-11-01, verified)

The `authors` account holds `challsRead`, but on the participant UI the
challenge list came back empty and opening a challenge answered `badChallenge`:
every participant endpoint hard-filters `hidden`/`releaseTime` for everyone, and
rCTF has no "preview as participant" mode or config key. This is the first
**Platform Patch** (ADR 0007) — a behavioural change on the fork, distinct from
a Skin Release.

- Release: git `a3082c1a` on branch `platform/author-preview`, tag
  `ingehack-author-preview-v1`, based on `ingehack-skin-v2` (so it carries the
  Skin too). Image `ghcr.io/otter-sec/rctf:ingehack-author-preview-v1`, shipped
  registry-less and kept at `/opt/rctf/images/ingehack-author-preview-v1.tar.gz`;
  deployed by `RCTF_GIT_REF=ingehack-author-preview-v1` + force-recreate.
  **Rollback**: `RCTF_GIT_REF=ingehack-skin-v2` (or `ingehack-skin-v1`, or
  `main`) + force-recreate; all older images remain on the VM.
- Change: `includeHidden` is plumbed through the participant challenge services
  and set from the caller's `challsRead` bit on `GET /v1/challs`, `GET
  /v2/challs`, the `/v1` and `/v2` solves routes, `GET /v2/challs/:id/scores`,
  `POST /v1/challs/:id/submit`, and the v2 instance lifecycle routes. Without
  the bit (no token or perms 0) the `hidden`/`releaseTime` filter is unchanged.
- Tests: `tests/server/tests/integration/challenge-visibility.test.ts` extended
  with list/solves/scores cases for a `challsRead` holder and a plain user;
  full server suite 648 pass. Types/api/web typecheck clean, lint/format clean.
- Verified live on `https://ctf.ingeniums.club` (anon and minted tokens):
  anonymous `GET /api/v2/challs` → 0 challenges; `authors` → all 16 (hidden
  included); a plain perms-0 account → 0. `sudoers` solves/scores: anonymous
  `badChallenge`, `authors` `goodChallengeSolvesV2` / `goodChallengeScoresV2`.
- Image parity: local build and VM-loaded image have identical md5 for
  `/app/apps/api/dist/index.js` and its source map, so the loaded image is the
  built one.


## Welcome challenge consolidation (2026-11-03, merged PR)

- The five-strong sanity-check family is now a single challenge:
  `challenges/misc/sanity-check/` — id `sanity-check` (static challenge, id is
  its `name`), shared container at
  `http://sanity-check.challs.ingeniums.club:9487/` /
  `https://…:9488/`, flag `ingehack{http_is_just_requests}`.
- It is the event's **welcome challenge** and pays **0 points**
  (`points: {min: 0, max: 0}`, `tiebreakEligible: false`) so finishing it never
  moves the scoreboard. rCTF's decay provider clamps to `[min, max]` and does
  not divide by `max - min`, so a 0/0 challenge is well-defined; raising it to
  100 is a one-line manifest edit (points changes are allowed while solves
  exist, unlike `scoring.kind`).
- Retired in the same merge (hide + wipe via the `retire` job; statics also get
  their `static-<dirname>` container torn down):
  `sanity-check-2`, `sanity-check-3`, `sanity-check-shared` (dir
  `hello-shared`), `sanity-check-instanced` (id `hello-instancer`, instanced —
  live per-team instances expire through `timeoutMilliseconds`).
- Consequence worth knowing: the beginner drills those directories demonstrated
  (local `path:` handout, R2 `url:` handout, per-team instanced flag, all three
  expose kinds) no longer have in-tree beginner exemplars. The real challenges
  still cover the shapes — `bulletproof-tenant-2` (description-only + local
  handouts), `keep-secrets`/`luckypatcher` (local handouts),
  `is-this-actually-pwn` (instanced + handout), `sudoers` (static raw TCP) —
  and the per-team flag path is exercised by any instanced challenge.
- Side effect: historical sections above still mention
  `hello-instancer`/`hello-shared` as the E2E fixtures; that is the record of
  what happened, not the current state.
