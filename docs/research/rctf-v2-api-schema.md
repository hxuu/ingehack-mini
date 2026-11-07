# rCTF v2 API / schema research (for CI challenge registration)

Sources: published docs at `https://rctf.osec.io` (raw `.md` variants) and
source code at `github.com/otter-sec/rctf` (cloned @ `main`, Oct 23 2026).
Cited per claim as docs page or repo file path (`packages/types/...` = repo
path `packages/types/src/...`; docs pages under `/api/...` are
`apps/docs/src/content/docs/api/...` `.md` raw equivalents).

## TOC

1. [Full admin route list](#1-full-admin-route-list)
2. [GET /api/v2/admin/instancer/schema](#2-instancer-schema-endpoint)
3. [Docker instancer `config` schema](#3-docker-tiny-instancer-config-schema)
4. [Scoreboard endpoint](#4-scoreboard-endpoint)
5. [Captcha / Turnstile config](#5-captchaconfig-turnstile)
6. [Create vs update semantics + rate limits](#6-create-vs-update-and-rate-limits)
7. [Implications for our CI register script](#7-implications-for-opsregister-challengesh)

---

## 1. Full admin route list

All admin routes are `Authorization: Bearer <auth-token>` user routes
(docs `/api/`, "Authentication"). Permission bits
(`packages/types/src/enums/permissions.ts`):

```
challsRead=1, challsWrite=2, leaderboardRead=4,
challsSolveWrite=8, usersWrite=16, settingsWrite=32
```

Every v2 admin route lives as `defineRoute` in
`packages/types/src/routes/v2/admin.ts` (exact paths/methods/permissions read
from that file; `(perm)` = required permission bit):

### Challenges
| Route | Perm | Notes |
|---|---|---|
| `GET /api/v2/admin/challs` | challsRead | List, no params (admin.ts:85). |
| `GET /api/v2/admin/challs/:id` | challsRead | Bad `badChallenge` for unknown id. |
| `GET /api/v2/admin/challs/:id/solves` | challsRead | query: `limit` int ≥1, `offset` int ≥0. |
| `PUT /api/v2/admin/challs/:id` | challsWrite | **Create or update** (upsert), see §6. |
| `GET /api/v2/admin/flags/providers` | challsRead | Flag provider name+JSON schemas. |
| `DELETE /api/v1/admin/challs/:id` | challsWrite | Only v1 has challenge delete (docs `/api/admin/`). |

### Update `/api/v2/admin/challs/:id` body — exact shape
Docs `/api/admin/challenge-update.md` + source `admin.ts:500-585`. Body:
`{ "data": { ... } }`; every field optional (partial update; omitted fields
keep current values — docs challenge-update note):

```json
{
  "data": {
    "name": "web demo",                 // string
    "category": "web",                  // string
    "author": "organizers",             // string
    "description": "Solve it.",         // markdown string
    "flags": [                          // full-list replacement (docs)
      { "provider": "flags/static",     // optional, default "flags/static"
        "config": { "flag": "flag{example}" } }
    ],
    "points": { "min": 100, "max": 500 },   // ints (schemas.ts:121)
    "tiebreakEligible": true,
    "files": [ { "name": "dist.zip", "url": "/uploads/dist.zip", "size": 12345 } ],
    "sortWeight": 10,
    "tags": ["beginner"],
    "hidden": false,
    "releaseTime": null,                // Unix ms int, or null
    "instancerConfig": { ... },         // null clears; see §2/§3
    "adminBotConfig": { "code": "admin-bot" },  // null clears
    "scoring": { "kind": "decay" }      // or {"kind":"dynamic","source":{...}}
  }
}
```

- **flags** (`packages/types/src/util/schemas.ts:250` `FlagEntrySchema`):
  `{ provider: string (default "flags/static"), config: record<string,any> }`.
  Providers (`apps/api/src/providers/flags/index.ts`): `flags/static`
  (config `{ "flag": string, minLength 1 }` — `static.ts:5`),
  `flags/regex` (config `{ pattern: string, flags?: string, flagValue?: string }`,
  `regex.ts:41`), `flags/dynamic` (per-team minted flags, `flags/dynamic/`).
  Passing `flags` replaces the whole list (docs challenge-update).
  Legacy scalar `flag` field still accepted (deprecated, mutually exclusive
  with `flags` — `update-challenge.ts:30-38`).
- **files** (`schemas.ts:40` `ChallengeFileSchemaV2`):
  `{ name: string, url: string, size: int|null }`. `size` is *technically
  optional for backwards compat with old data* (schemas.ts:45 comment), and
  `null` means "unknown" — the docs example always sends it. Our CI should
  always send `size` (int).
- **points** required fields only when present: `{min:int, max:int}`
  (schemas.ts:121).
- **scoring** (`schemas.ts:146`): discriminanted union
  `{ "kind": "decay" }` or
  `{ "kind": "dynamic", "source": { "transport": "webhook", "secret": "..." } }`.
- **hidden**: bool (default false). **releaseTime**: nullable Unix-ms int.
  **sortWeight**: int (higher sorts first). All three are opt-in in our payload
  builder: the key is omitted unless `chall.yaml` declares it, because rCTF's
  upsert keeps the current value for an undefined key and only clears it on an
  explicit null. That lets an admin-UI edit survive CI re-registration; a
  manifest value still overrides.
- Response `goodChallengeUpdateV2`: `data` = full
  `AdminChallengeSchemaV2` (`responses/good-challenge-update-v2.ts`), incl
  `id`, files with nullable `size`, `hidden` (null→false,
  `update-challenge.ts:157`).
- `instancerConfig`/`adminBotConfig` validated against the active provider
  before saving; `badInstancerConfig`/`badAdminBotConfig` on failure
  (`update-challenge.ts:59-84`).

### Instancer (admin, challenges)
All under `challsRead` only, and operate on the **authed admin's own team**
(no `teamId` param — docs `/api/admin/instance-start.md`:
"starts an instance for the authenticated admin's own team").

| Route | Method/Path |
|---|---|
| Status | `GET /api/v2/admin/challs/:id/instance` |
| Start | `PUT /api/v2/admin/challs/:id/instance` — **no body** |
| Extend | `PATCH /api/v2/admin/challs/:id/instance` — no body |
| Stop | `DELETE /api/v2/admin/challs/:id/instance` |
| Action | `POST /api/v2/admin/challs/:id/instance/actions/:action` |

(admin.ts:415-498). Only path `params` — no query/body params. Response
`goodInstanceStatus` (`responses/good-instance-status.ts`):

```json
{ "kind": "goodInstanceStatus",
  "data": { "status": "running",       // stopped|running|starting|stopping|errored
             "timeLeftMilliseconds": 600000,
             "endpoints": [ { "kind": "tcp", "host": "x", "port": 1337,
                              "title": "nc", "text": "nc x 1337" } ] } }
```

### Users
| Route | Perm |
|---|---|
| `GET /api/v2/admin/users` | usersWrite; query `limit` (1-100), `offset`, `search`, `sortBy` (createdAt\|team\|email\|division\|score\|solves\|status), `sortOrder` |
| `POST /api/v2/admin/users` | same query + body `{status:{include,exclude}, division:{include,exclude}}` (admin.ts:116) |
| `GET /api/v2/admin/users/:id` | usersWrite+challsRead |
| `PUT /api/v2/admin/users/:id` | usersWrite; body `{data:{banned?,name?,division?,countryCode?,statusText?}}` |
| `DELETE /api/v2/admin/users/:id` | usersWrite — **full delete exists** (admin.ts:331; `goodAdminUserDeleteV2`). `badUserPrivileged` if target is an admin. |
| `PATCH /api/v2/admin/users/:id/avatar` | multipart |
| `POST /api/v2/admin/users/:id/token` | mint a token for that team |
| `DELETE /api/v2/admin/users/:userId/solves` | challsSolveWrite — delete **all** solves of a team |
| `GET /api/v2/admin/user-verifications` (+ `/:id/complete`, `/:id/resend`) | usersWrite |

So: to delete test users → `DELETE /api/v2/admin/users/:id` per user; no bulk
delete route exists (nothing wider in admin.ts). Note `banned` is also the
"disable" mechanism (`PUT ... {data:{banned:true}}`).

### Solves / submissions
| `DELETE /api/v2/admin/challs/:challengeId/solves/:userId` | challsSolveWrite (admin.ts:612) |
| `GET/POST /api/v2/admin/submissions` | usersWrite+challsRead; pagination + rich filter body (docs `/api/admin/`) |

### Upload
- `POST /api/v2/admin/upload` — `multipart/form-data`, one or more `files`
  fields; `challsWrite`; dedup by SHA-256; response data =
  array of `{name,url,size}` (`goodFilesUploadV2`, docs `/api/admin/upload.md`).
- `POST /api/v2/admin/upload/query` — JSON body
  `{ "uploads": [ { "sha256": "...", "name": "..." } ] }`, challsRead.

### Settings
`GET /api/v2/admin/settings` / `PUT` (settingsWrite). PUT body
`{data:{ctfName?,homeContent?,startTime?,endTime?,sponsors?,meta?,faviconUrl?,logoLightUrl?,logoDarkUrl?}}`
— all nullish-optional (admin.ts:743-785).

### Admin bot / external auth (service-token or usersWrite)
`GET .../admin-bot/status`, `POST .../admin-bot/jobs/pull`,
`GET .../admin-bot/challenges/:id/source`, `POST .../admin-bot/jobs/:id/complete|fail`,
`GET .../admin-bot/queue-depth` (service auth). External-auth clients
`GET/POST /api/v2/admin/external-auth/clients`, `DELETE .../clients/:id`
(usersWrite).

## 2. Instancer schema endpoint

`GET /api/v2/admin/instancer/schema`, challsRead (admin.ts:646). 404
`badEndpoint` when no instancer configured (docs `/api/admin/instancer-schema.md`).
Response `goodInstancerSchema` (`responses/good-instancer-schema.ts`):

```json
{ "kind": "goodInstancerSchema",
  "data": {
    "defaultInstancer": "docker-instancer",
    "instancers": [ {
      "name": "docker-instancer",
      "schema": { "type": "object", "properties": { ... } },  // JSON Schema
      "defaults": { "services": { "app": { ... } }, "networks": {}, "volumes": {} },
      "canStop": true, "canExtend": true,
      "actions": [ { "id": "restart", "label": "Restart" } ] } ] } }
```

The `schema` entries are JSON Schemas derived from the provider's zod schema —
this is the endpoint CI should validate `instancerConfig.config` against pre-PUT
(the admin panel uses it for the same purpose, docs instancer-schema page).

## 3. Docker (tiny) instancer `config` schema

Challenge-side envelope (`schemas.ts:211` `InstancerConfigSchema`,
`:230` partial variant used in PUT):

```json
{
  "challengeIntegrationId": "baby-rev",   // required in InstancerConfigSchema (full); optional in PUT (PartialInstancerConfigSchema)
  "instancer": "docker-instancer",        // optional; default instancer if omitted
  "config": { ...provider-specific... },
  "expose": [ {
    "kind": "tcp",                        // tcp|tcp-ssl|http|https|raw (schemas.ts ExposeKind)
    "hostPrefix": "baby-rev",             // ^[a-z0-9-]+$ , max 63
    "containerName": "main",              // must be a key of config.services
    "containerPort": 1337,                // 1-65535
    "shouldDisplay": true,                // optional bool
    "title": "nc" } ],                    // optional label
  "timeoutMilliseconds": 600000,          // instance lifetime
  "extendable": true
}
```

`config` for `docker-instancer` (`apps/api/src/providers/instancer/docker-instancer.ts:1-440`,
`tinyInstancerConfigSchema`; instance-side pydantic mirror
`apps/docker-instancer/instancer/protocol/types.py` `InstancerConfig`).
Top level: `{ services: record<string, Service>, networks: record<string, Network>, volumes: record<string, Volume> }`;
`services` must be non-empty; service `networks` entries must exist in
`networks`; service volume mounts referencing a named volume must exist in
`volumes` (refines at docker-instancer.ts:430-440). Defaults from
`configSchema.parse({})` (`getDefaults`, line 466): `services: { app: {...} }`.

Service fields (name — type, default):
`image` (string, required, Docker-image regex) · `hostname` (str|null, null)
· `environment` (map env-var-name→str, {}) · `command` (str|list|null, null)
· `entrypoint` (str|list|null, null) · `working_dir` (abs path|null, null)
· `user` (str|null, null) · `networks` (list[str], []) · `network_mode`
(str|null — default service sets `'none'`) · `dns`, `dns_opt`, `dns_search`
(list[str], []) · `extra_hosts` (list `"host:ip"`, []) · `expose`
(list of port strings e.g. `"1337/tcp"` — "Expose ports without publishing",
[]) · `volumes` (list `"volume:path"`/"host:path"/abs-path mounts, []) ·
`tmpfs` (map abs-path→mount-opts, {} incl `{'/tmp': 'rw,noexec,...size=65536k'}`)
· `shm_size` ("64m"-style, null) · `healthcheck`
(`{test:[str], interval:"30s", timeout:"10s", retries:3, start_period:"0s"}`, null)
· `read_only` (bool, **true**) · `privileged` (bool, false) ·
`security_opt` (list[str], `['no-new-privileges']`) · `cap_add`
(list of Linux caps, []) · `cap_drop` (`['ALL']`) · `mem_limit`
("6m"-style; **default is 6m — usually must be raised**, e.g. `"256m"`) ·
`cpus` (float, 1.0) · `pids_limit` (int, **64** in the TS schema / 1024 in the
Python protocol model) · `ulimits` (map ulimit-name→`{soft,hard}`, default
`nofile 1024/1024`) · `sysctls` (map, {}) · `labels` (map, {}) ·
`restart` (`no|always|on-failure|unless-stopped`, `unless-stopped`).

Networks: `{ driver: bridge|host|none (bridge), internal: bool (true), driver_opts: map }`.
Volumes: `{ driver: local|nfs|tmpfs (local), driver_opts: map }` (note: the
TS provider enum is `nfs`, the Python protocol model has only local — TS side
is what validates challenge config).

REST between rCTF↔instancer (`protocol/types.py`): create form carries
`rctfAuthToken`, `teamId`, `challengeIntegrationId`, `config`, `expose`,
`flags` (per-team minted flags — this is how `${RCTF_FLAG}`-style dynamic
flags get injected), `timeoutMilliseconds`.

## 4. Scoreboard endpoint

`/api/v2/leaderboard` (no sub-path) is not a route. Real routes
(`packages/types/src/routes/v2/leaderboard.ts`; docs `/api/leaderboard.md`):

| Route | Notes |
|---|---|
| `GET /api/v2/leaderboard/now` | query `limit`, `offset`, `division?`, `search?` (2-100 chars, rate-limited burst 3 / 3000 ms per IP) |
| `GET /api/v2/leaderboard/with-graph` | adds `challenge?` filter |
| `GET /api/v2/leaderboard/graph` | `limit`,`offset`,`division?` |
| `GET /api/v2/leaderboard/challs` | challenge meta (points/places) |
| `GET /api/v1/leaderboard/now`, `/graph` | v1 equivalents |
| `GET /api/v1/integrations/ctftime/leaderboard` | `{standings:[...]}` (leaderboardRead) |

Response `goodLeaderboardV2` (`responses/good-leaderboard-v2.ts`):

```json
{ "kind": "goodLeaderboardV2", "data": {
  "total": 128,
  "leaderboard": [ { "id": "team-...", "name": "otter-sec",
    "score": 13370, "avatarUrl": null, "countryCode": null, "statusText": null,
    "solves": [ { "id": "baby-rev", "solveTime": 1710000000000 } ],
    "dynamicScores": [ { "id": "...", "points": 487, "pointDelta": -13 } ],
    "division": "open", "divisionPlace": 3, "globalPlace": 7 } ] } }
```

Player-facing scoreboard UI uses `v2/leaderboard/now` (+with-graph).
All start-gated (`badNotStarted` before startTime); admins with
`leaderboardRead` bypass (docs leaderboard page).

## 5. Captcha config (`captcha`)

Config type (`packages/config/src/types.ts:103-117`):

```json
"captcha": {
  "provider": {
    "name": "captcha/turnstile",
    "options": { "secretKey": "<secret>", "siteKey": "<siteKey>" }
  },
  "protectedEndpoints": ["register", "instancerStart", "instancerExtend"]
}
```

- `ProtectedAction` enum (`packages/types/src/enums/captcha.ts`):
  `register`, `recover`, `setEmail`, `instancerStart`, `instancerExtend`,
  `avatarUpload`, `adminBotSubmit`. `protectedEndpoints` defaults to *all* if
  omitted (types.ts:110) — better to be explicit.
- Turnstile provider (`apps/api/src/providers/captcha/turnstile.ts`): options
  `secretKey`/`siteKey`, overridable by env `RCTF_TURNSTILE_SECRET_KEY` /
  `RCTF_TURNSTILE_SITE_KEY`; validates via Cloudflare `siteverify`; browser
  needs CSP `frame-src https://challenges.cloudflare.com`. Registered under
  name `captcha/turnstile` (`captcha/index.ts`). Legacy `recaptcha` config is
  backported to `captcha/recaptcha` (`config/src/normalize.ts:5`).
- Client sees (public, `goodClientConfigV2`):
  `captcha: { provider: string, publicOptions: { siteKey }, protectedEndpoints: { register: true, ... } }`
  (`responses/good-client-config-v2.ts`). Client sends the widget token in
  the request **body field `captchaCode`** on v2 routes — `POST /api/v2/auth/register`
  (`routes/v2/auth.ts:45`), `PUT /api/v2/integrations/challs/:id/instance`
  (integrations.ts:57), `PATCH .../instance` (integrations.ts:97),
  `POST .../challs/:id/admin-bot` (integrations.ts:208). v1 used
  `recaptchaCode` (docs `/api/`).

## 6. Create vs update, and rate limits

- `PUT /api/v2/admin/challs/:id` **creates when the id does not exist**
  (`upsertChallenge` — `apps/api/src/services/challenges.ts:435-504`;
  route handler calls it for both cases, docs
  `/api/admin/challenge-update.md`: "This route creates a new challenge or
  updates an existing one."). So one PUT with the **id** = the challenge's
  stable integration id is correct for CI create *and* update. `DELETE
  /api/v1/admin/challs/:id` is the only delete (v1).
- Semantics: omitted top-level challenge fields keep current values for an
  existing challenge (docs); for a create, `instancerConfig` object is merged
  over `defaultInstancerConfig` (services.ts:486-495), `adminBotConfig`
  replaces. Changing `scoring.kind` is blocked while solves exist
  (`badBody` reason `scoring:kind:...`, services.ts:429-433).
- Rate limits relevant to registration-time CI: the registration-email
  buckets (burst 20/600 s per IP; burst 2/3600 s per email) apply only when a
  verification email would be sent (docs `/api/`) — admin PUT challs has no
  rate limit listed. `adminBotSubmit` burst 1/10 s. Nothing limits a PUT now.
- File upload dedup means re-registering after a handout change needs only
  changed files re-uploaded (`/api/admin/upload.md`).

## 7. Implications for ops/register-challenge.sh

Current script sends a v1-era/other-platform payload; mismatches vs the
verified schema:

1. Wrong/unknown field names in the payload builder: `type`
   (should be absent or `tiebreakEligible`), `imageUrl`, `scores`
   (correct block is `points: {min,max}`), `individuallyInstanced`
   (doesn't exist — instancing per challenge is driven by presence of
   `instancerConfig`), and `files[].path` (must be `files[] =
   {name,url,size}` with a public URL — upload first via
   `POST /api/v2/admin/upload`, use returned `url`, keep `size`).
2. Flags: must be `"flags": [{ "provider": "flags/static", "config": { "flag": "..." } }]`
   (or `flags/regex`/`flags/dynamic`), not a scalar.
3. `challengeIntegrationId` lives *inside* `instancerConfig`, and
   `instancerConfig.config` must match the docker-instancer schema of §3
   (services/networks/volumes; mind `mem_limit` default "6m" and
   `read_only:true`, `cap_drop:['ALL']` defaults breaking most services).
   Validate `config` in CI against the live `GET /api/v2/admin/instancer/schema`
   JSON Schema before PUT.
4. `challenge_id` for the URL should be the challenge's stable id (the script
   already derives it from `challengeIntegrationId` — fine).
5. Create-or-update via one `PUT /api/v2/admin/challs/:id` — no
   create/upsert branching needed; settings like `hidden` belong in `data`
   (`{data:{...}}` wrapper).
6. If Turnstile is enabled with `instancerStart`/`instancerExtend` protected,
   admin instance routes are unaffected (only the player routes send
   `captchaCode`); registration of test accounts during rehearsals needs a
   `captchaCode` only if `register` is in `protectedEndpoints`.
7. Test users: `DELETE /api/v2/admin/users/:id` (perm usersWrite; fails
   `badUserPrivileged` for admins) — plus
   `DELETE /api/v2/admin/users/:userId/solves` to wipe a team's solves.
