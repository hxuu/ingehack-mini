# rCTF v2 — TLS handling and a zero-dollar, no-payment-verification deployment

Research date: 2026-10-23. Companion to `docs/status.md`.
Claims citing only websearch results (not directly fetched primary pages) are explicitly marked **⚠ unverified**.

---

## Constraints

- **Zero dollars.** Every service used must be on a permanently free tier.
- **No payment verification.** No credit card / PayPal / mastercard / fee-based identity check disclosed to *any* vendor (no card even for an "upgrade later" style account verification).
- Consequence: paid Cloudflare add-ons (Advanced Certificate Manager, Total TLS, Spectrum, custom-cert upload plan tiers) are out, even if nominally cheap.

---

## 1. What rCTF's own docs say about TLS termination

### Platform (rCTF container) — architecture

Source: https://rctf.osec.io/installation/architecture

- The rCTF container bundles nginx inside (supervisord program), which serves the SvelteKit static build and proxies `/api` and `/uploads` to the Hono API on `:3000` — but **nginx inside the container only listens on HTTP port 80, not TLS**.
- "The `rctf` service exposes `127.0.0.1:8080` and expects a reverse proxy (typically nginx or Caddy on the host) to **terminate TLS** and forward to it."

→ TLS for the platform is always terminated *outside* rCTF: host nginx/Caddy, or a Cloudflare Tunnel (cloudflared then fronts it).

### VPS walkthrough — "Setting up a CTF platform"

Source: https://rctf.osec.io/meta/running-a-successful-ctf/setup (edit page: `apps/docs/src/content/docs/meta/running-a-successful-ctf/setup.md`)

The official walkthrough gives **two TLS options for the platform host**:

1. **Cloudflare-proxied hostname** (orange cloud):
   - Proxied `A` record, SSL/TLS mode `Full (strict)`.
   - **Cloudflare *Origin Certificate*** created under SSL/TLS → Origin Server, saved as `/etc/ssl/cf_fullchain.pem` + `/etc/ssl/cf_privkey.pem`, installed on host nginx. Origin certs are free and are *only trusted by Cloudflare* — good enough because UFW whitelists only Cloudflare's IPs (the doc quotes `curl https://www.cloudflare.com/ips-v{4,}` for the ufw rules).
   - nginx uses `set_real_ip_from 0.0.0.0/0; real_ip_header CF-Connecting-IP;` and is told it is *very* important to whitelist only Cloudflare IPs, otherwise the IP is spoofable.
2. **Certbot (Let's Encrypt)** — the doc links https://certbot.eff.org/instructions as the alternative when not sitting behind CF.

Other notes from the same guide (and siblings in `/meta/running-a-successful-ctf/`):

- rCTF config: enable `proxy.cloudflare` when behind Cloudflare.
- Deployment guide (`/meta/running-a-successful-ctf/deployment`): do **not** put intentionally vulnerable challenges on the platform server; shared remotes need jails (pwn.red/jail or nsjail); instanced remotes via **Docker instancer** (recommended for small-to-medium events) fit this split-VM design.
- Teardown guide (`/meta/running-a-successful-ctf/after-ctf`) mentions deleting "the ACME wildcard secret" (k8s) — i.e., wildcard ACME certs are the house-standard for instancers.
- **No page in `/meta` recommends paid Cloudflare features or free-hosting vendors.** The only "free" guidance is the GCP CTF sponsorship link in `/prerequisites`.

### Docker instancer — TLS details

Source: https://rctf.osec.io/integrations/instancer/docker (edit page: `apps/docs/src/content/docs/integrations/instancer/docker.md`)

All the claimed details check out, with one correction on *where* `watch: false` lives:

| Claim | Verdict |
|---|---|
| Compose stack exposes Traefik on `80`, `443`, `1337`; instancer API binds `127.0.0.1:12237` in the default setup, change to `'12237:1337'` when split-host | ✅ confirmed both in the doc page and `deploy/docker-instancer/compose.yml` (upstream comment says "If you're hosting tiny-instancer separately (which you should), expose this globally and make sure to put a firewall") — https://raw.githubusercontent.com/otter-sec/rctf/main/deploy/docker-instancer/compose.yml |
| Traefik loads `certs/fullchain.pem` + `certs/privkey.pem` from the mounted `certs/` dir | ✅ `deploy/docker-instancer/conf/tls.yml` is exactly 100 bytes: `tls.certificates: [{certFile: '/certs/fullchain.pem', keyFile: '/certs/privkey.pem'}]` — https://raw.githubusercontent.com/otter-sec/rctf/main/deploy/docker-instancer/conf/tls.yml |
| `watch: false` so renewals need a Traefik **restart** | ✅ but note: the `watch: false` is in the **static config** `conf/traefik.yml` (`providers.file.watch: false`), *not* in `conf/tls.yml` itself. Upstream `conf/tls.yml` contains only the cert pair. Same net effect: file-provider dynamic config is not watched → **restart the Traefik container after renewing**. — https://raw.githubusercontent.com/otter-sec/rctf/main/deploy/docker-instancer/conf/traefik.yml |
| Instance hostnames are `<prefix>-<uid>.<INSTANCES_HOST>`, one label deep, so `*.<INSTANCES_HOST>` covers every instance | ✅ confirmed in source: `apps/docker-instancer/instancer/core/instancer/traefik.py`, function `expose_host()` → `f'{expose.host_prefix}-{instance_id}.{config.INSTANCES_HOST}'` with `instance_id = uuid.uuid4().hex[:12]` (https://raw.githubusercontent.com/otter-sec/rctf/main/apps/docker-instancer/instancer/core/instances.py). Docs page states it verbatim. |
| Wildcard cert cannot use HTTP-01; recommend DNS-01 (`certbot certonly --manual --preferred-challenges dns -d '*.instancer.example.com'`) | ✅ doc page + Let's Encrypt: "This challenge cannot be used to issue wildcard certificates." — https://letsencrypt.org/docs/challenge-types/ |

### Endpoint kinds and what actually needs TLS

Sources: https://rctf.osec.io/integrations/instancer (endpoint-kind table) and `apps/docker-instancer/instancer/core/instancer/traefik.py` (`expose_ports()`):

| kind | Router | TLS? |
|---|---|---|
| `http` | Traefik HTTP router, entrypoint `web` (=80), rule `Host(...)` | **No TLS** — plain HTTP through Traefik:80 |
| `https` | Traefik HTTPS router, entrypoint `websecure` (=443), `tls: 'true'` | Yes (static cert); adds a 80→443 redirect router unless an `http` expose with the same prefix exists |
| `tcp` | **Rewritten to `tcp-ssl`** because Traefik needs SNI routing | Yes |
| `tcp-ssl` | Traefik TCP router, entrypoint `tcp` (=1337), `HostSNI('<host>')`, `tls: 'true'` | Yes (static cert; SNI matches the wildcard) |

Key consequences:

- **`http` endpoints can avoid TLS entirely** — a `http` expose serves plain HTTP on Traefik:80 and can sit behind an orange-cloud Cloudflare proxy (CF terminates TLS at its edge with its own Universal cert). This is why the rCTF docs' `RCTF_EXPOSED_HOSTNAMES` lists raw `kind`/`host`/`port` and why `tcp` is coerced to `tcp-ssl` (source: `coerce_tcp_exposes()`).
- `https` and `tcp-ssl` both depend on the single static wildcard pair in `certs/`.

### Does the instancer support per-instance / on-demand ACME certs (e.g. Traefik ACMA, DNS-challenge)?

**No, not out of the box.**

- Traefik static config (`conf/traefik.yml`) defines no `certificatesResolvers` / ACME block at all — the only certificate source is the static file pair (`conf/tls.yml`).
- The dynamic file config is loaded with `watch: false`, so even a traded-in cert file would require a restart.
- The instancer cannot inject ACME settings; it only writes Docker **labels** (`traefik.http.routers.<name>.rule = Host('...')`, `traefik.tcp.routers.<name>.rule = HostSNI('...')` — see `expose_ports()` in `traefik.py` above). It performs no certificate issuance, no ACME calls, and does not document a `custom conf overrides` mechanism.
- The documented intended path is exactly what the docker-instancer page says: **one DNS-01 wildcard cert for `*.<INSTANCES_HOST>`, copy into `certs/`, restart Traefik** on renewal.
- It *is* possible to replace `conf/tls.yml` / edit `conf/traefik.yml` yourself to add a `certificatesResolvers` ACME block with a DNS challenge (this is plain Traefik config, mounted from host paths you control), but that is undocumented and unsupported by the docs. Nothing prevents it technically — it would just move cert issuance out of the docs' manual-copy flow.

---

## 2. Cloudflare free-tier facts (all verified against developers.cloudflare.com)

### Proxied-ports whitelist

Source: https://developers.cloudflare.com/fundamentals/reference/network-ports

- HTTP ports proxied by default: **80, 8080, 8880, 2052, 2082, 2086, 2095**
- HTTPS ports proxied: **443, 2053, 2083, 2087, 2096, 8443**
- Other ports: only via **gray-clouding** the record to bypass CF (direct to origin), or paid **Spectrum** ("Spectrum for all TCP/UDP ports only on Enterprise").

→ rCTF instancer's Traefik ports 443 and 80 are fine proxied; **1337 (tcp-ssl) is NOT proxyable** — pwn traffic must be gray-cloud/direct to a mapped port.

### Universal SSL host coverage depth

Source: https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/limitations

- "coverage is limited to the **root domain** (`example.com`) and **first-level subdomains** (`www.example.com`)… Deeper subdomains — such as `dev.www.example.com` — are **not** covered and will not serve a valid certificate."
- To cover deeper subdomains you must buy **Advanced Certificate Manager** or **Total TLS**, or upload a custom cert (also a paid-plan feature). **⚠ unverified exact price** ($10/mo is the widely-quoted ACM add-on price; not stated on the pages fetched here — appears in community threads and older CF pages, e.g. https://community.cloudflare.com/t/how-can-i-get-ssl-for-multi-level-subdomains/582057).
- ECDSA-only on Free plan (from the same page), and wildcard DCV uses TXT validation (from https://developers.cloudflare.com/dns/manage-dns-records/reference/wildcard-dns-records).

### Wildcard DNS records (proxying) are free on all plans

Source: https://developers.cloudflare.com/dns/manage-dns-records/reference/wildcard-dns-records — "Customers on **all plans** can create and proxy wildcard DNS records." (i.e., no plan gate on the *record*; the plan gate is on the *edge certificate* coverage, above.)

### Cloudflare Tunnels

Source: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/

- Free, self-service; tunnels are a Zero Trust feature with a **Zero Trust Free** plan (limits table lists "Zero Trust Free" explicitly: https://developers.cloudflare.com/cloudflare-one/account-limits).
- You create the tunnel in the dashboard, run the install command ("copy the installation command and run it in a terminal on your origin server"), then add a **published application route**: hostname + **Service URL** like `http://localhost:8000`.
- Certificate install to the origin transport: **none needed** — cloudflared terminates TLS for *your* published hostname at the CF edge; the origin side uses the service URL protocol, plain `http://` is a supported protocol. So no origin cert, no card.
- Caveat documented on the same page: "**If you add a multi-level subdomain (more than one level of subdomain), you must order an Advanced Certificate for the hostname**" — i.e. tunnel published hostnames must be ≤ 2 labels under the zone apex or you pay.
- Prerequisite: the zone must be added to Cloudflare ("you must add a website to Cloudflare").
- **⚠ unverified**: whether creating a Zero Trust account on the free plan requires any card/no-fee identity check. No CF doc page retrieved mentions card requirements for Cloudflare Tunnel or Zero Trust Free; community reports say the Zero Trust free signup requires no payment method. Treat as *believed true, not doc-verifiable*.

### DNS API token without payment info

Source: https://developers.cloudflare.com/fundamentals/api/get-started/create-token/

- API tokens are created from **My Profile → API Tokens → Create Token**, using the **"Edit zone DNS" template**, with per-zone resource scoping ("granting Zone DNS Read access to a zone `example.com` will allow the token to read DNS records only for that specific zone").
- DNS record creation is a free plan feature (free plan includes the full DNS product); the API token flow itself involves no billing. **⚠ unverified (not doc-verifiable)**: that a Cloudflare *free-plan account* signup collects only an email address and no card — docs don't discuss signup billing; empirically the CF free signup asks for email only.

---

## 3. Let's Encrypt vs alternatives (free, no payment)

- **Let's Encrypt**: free, ACME. DNS-01 needed for wildcards ("This challenge cannot be used to issue wildcard certificates" applies to HTTP-01; DNS-01 "allows you to issue wildcard certificates") — https://letsencrypt.org/docs/challenge-types/. ACME *account registration* requires only a free account key (no email/card via the ACME protocol itself).
- **ZeroSSL**: `zerossl.com/pricing` states the Free plan is "$0/month… **Start today without credit card required**" with 90-day ACME certificates available "on all plans" (FAQ: "If you have a server or other device that requires automatic issuance of certificates and supports the ACME protocol, you can use our free 90-day ACME certificates on all plans"). Dashboard quota shown as 3 free certs; via ACME it functions as the free alternative CA in certbot/lego. Usable with no payment method.
- **BuyPass Go SSL**: ⚠ **discontinued as a free option since 2025** — official page: "October 16, 2025: TLS/SSL certificates can no longer be ordered, renewed, or replaced… Buypass has decided to terminate the service for issuing TLS/SSL Certificates, including Go SSL (ACME)." https://www.buypass.com/products/tls-ssl-certificates/discontinues-issuance-of-tls-ssl-certificates. Do not plan around BuyPass.
- **Certbot's Cloudflare DNS plugin** automates DNS-01 by creating/removing the `_acme-challenge` TXT records via the CF API: https://certbot-dns-cloudflare.readthedocs.io/ (⚠ fetched only via search result snippets; the plugin's existence and DNS-01 TXT automation is corroborated by EFF/community docs).

Conclusion: **Let's Encrypt + Cloudflare DNS API (direct ACME account, no dashboard signup to LE needed) is the only path we need; ZeroSSL is the documented no-card fallback.**

---

## 4. Synthesis for inge-minictf's split-host deployment

Current state (from `docs/status.md`): platform VM `10.0.47.5` (/opt/rctf compose) behind a running CF Tunnel; challs VM `10.0.47.2` (/opt/rctf-src deploy/docker-instancer) with Traefik 80/443/1337, `INSTANCES_HOST=105.98.65.136.nip.io` and a self-signed wildcard in `certs/`.

Depth math that drives the design:

- rCTF instance hostnames are one label under `INSTANCES_HOST` → for INSTANCES_HOST=`challs.ingeniums.club` they are `hello-<uid>.challs.ingeniums.club` — **3 labels under the zone apex** → Universal SSL does NOT cover them (limitations page above), orange-cloud proxying is blocked without ACM/Total TLS, and a CF Tunnel published hostname for that depth is likewise blocked (needs an advanced cert). Cloudflare's free path has **no** no-card way to serve a valid edge TLS cert 3 labels deep.
- Implication: for web instancer endpoints, either (a) **gray-cloud + LE wildcard on the origin** (recommended, below), or (b) orange + `http` kind behind CF — but breaking 3-label depth means **(b) is only viable if the CF Tunnel route issues its own edge cert at ≤ 1-level subdomain, e.g. by setting `INSTANCES_HOST` to a first-level hostname under an added CF zone** (e.g. use `*.example2.com` as the zone where instances are 1 label deep). In our single-zone `ingeniums.club` case, plan (a).

### Mandatory certs, and only them

| Path | TLS needed at origin? | How |
|---|---|---|
| Platform web (`ctf.ingeniums.club`) | Yes (or none if tunnel-only) | existing CF Tunnel (already running) → no origin cert needed provided the published route is ≤1-level (`ctf.ingeniums.club` is 1-level: fine). *(Alt: host nginx + Let's Encrypt certbot DNS-01 wildcard if we ever want direct 443)* |
| Challs **web** instancer endpoints (`kind: https`) | **Yes — LE wildcard `*.challs.ingeniums.club` on the challs Traefik**, gray-cloud | DNS-01 via CF API token |
| Challs **pwn tcp-ssl** (`pwn` → coerced tcp-ssl, port 1337) | **Yes — same LE wildcard** (SNI matches) | gray-cloud mapped port 1337; CF cannot proxy :1337 (not in whitelist) |
| Challs **web** endpoints of kind `http` | No | could be orange + CF edge cert only if ≤1-level — with our naming depth, avoid |

So only **one** certificate is mandatory: the wildcard `*.challs.ingeniums.club` (plus optionally the SAN `challs.ingeniums.club`).

### Migrations needed

Challs VM (`/opt/rctf-src/deploy/docker-instancer/` — files in scope):

1. `compose.yml` — keep `12237:1337` instancer bind (already done, split-host mode). Review `$TRAEFIK_HTTPS_PORT` etc. (defaults 80/443/1337 match OpenScaler mapping).
2. `.env` — `INSTANCES_HOST=challs.ingeniums.club`.
3. `certs/` — replace self-signed nip.io files with the Let's Encrypt `fullchain.pem` + `privkey.pem` (same filenames; `conf/tls.yml` needs no change).
4. OpenScaler port mappings: keep/derive 443→Traefik:443 and 1337→Traefik:1337; the auto-assigned public ports are recorded in `docs/status.md`.
5. (Optional) cloudflared on the challs VM only if you go the tunnel route for instanced web — not needed for the recommended gray-cloud topology.
6. Firewall: keep `12237` reachable only from `10.0.47.5` (status.md pending item).

Platform VM (`/opt/rctf/` — files in scope):

7. `rctf.d/02-ctf.yaml` — `origin: https://ctf.ingeniums.club` (currently http on mapped port) — this also clears the known plain-HTTP 500 bug (KCS `crypto.randomUUID()` non-secure-context).
8. `rctf.d/04-instancer.yaml` — no cert changes; same shared token.
9. `proxy.cloudflare` option per the setup guide, since traffic arrives via Cloudflare.

DNS (Cloudflare zone `ingeniums.club`, free plan, all records creatable on free):

- `ctf` A/CNAME (current tunnel or mapped port)
- `*.challs` A → `105.98.65.136` **DNS-only (gray cloud)** — 3-label depth would break orange anyway
- optional `challs` A (same) so the bare challs host resolves
- `attachments` → R2 bucket per status.md

### Cert issuance + reload commands (copy-paste)

On the challs VM, one-time setup (Ubuntu, certbot + Cloudflare plugin):

```bash
# on minictf-challs
apt update && apt install -y certbot python3-certbot-dns-cloudflare

# Cloudflare API token — create in dashboard with the "Edit zone DNS" template,
# zone-scoped to ingeniums.club only. Docs: developers.cloudflare.com/fundamentals/api/get-started/create-token
mkdir -p /root/.secrets && cat > /root/.secrets/cf-dns.ini <<'EOF'
# Cloudflare API token, scoped to Zone:DNS:Edit for ingeniums.club only
dns_cloudflare_api_token = <PASTE_TOKEN_HERE>
EOF
chmod 600 /root/.secrets/cf-dns.ini
```

Issue the wildcard (DNS-01 — required for wildcards, letsencrypt.org/docs/challenge-types):

```bash
certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /root/.secrets/cf-dns.ini \
  -d challs.ingeniums.club \
  -d '*.challs.ingeniums.club'
```

Install into the Traefik mount (exact filenames expected by `conf/tls.yml`):

```bash
cd /opt/rctf-src/deploy/docker-instancer
cp /etc/letsencrypt/live/challs.ingeniums.club/fullchain.pem certs/fullchain.pem
cp /etc/letsencrypt/live/challs.ingeniums.club/privkey.pem  certs/privkey.pem
```

Traefik loads the pair at startup and does **not** watch the file config (`providers.file.watch: false` in `conf/traefik.yml`), so **restart** Traefik after each issuance or renewal — the official docs state this verbatim ("Traefik loads these at startup and doesn't watch the file config (`watch: false`), so restart the Traefik container after renewing or replacing the certificate"):

```bash
docker compose -f /opt/rctf-src/deploy/docker-instancer/compose.yml restart traefik
```

Automation — add a certbot deploy hook so every renewal also restarts Traefik:

```bash
cat >/etc/letsencrypt/renewal-hooks/deploy/rctf-instancer.sh <<'EOF'
#!/bin/sh
set -e
cd /opt/rctf-src/deploy/docker-instancer
cp /etc/letsencrypt/live/challs.ingeniums.club/fullchain.pem certs/fullchain.pem
cp /etc/letsencrypt/live/challs.ingeniums.club/privkey.pem  certs/privkey.pem
docker compose -f /opt/rctf-src/deploy/docker-instancer/compose.yml restart traefik
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/rctf-instancer.sh
```

(Lego equivalent, if you prefer Go tooling — also free, no account payment:

```bash
lego --dns cloudflare -d challs.ingeniums.club -d '*.challs.ingeniums.club' run
```
)

### Recommended topology, in one paragraph

Platform VM hosts rCTF fronted by the already-running **CF Tunnel** at `ctf.ingeniums.club` (1-level hostname → Universal SSL edge cert covers it; origin protocol is plaintext `http://localhost:…` — no cert install needed, tunnel docs cite `http://localhost:8000` service URLs as supported). Challs VM keeps the official **docker-instancer compose** with Traefik 80/443/1337; `INSTANCES_HOST=challs.ingeniums.club`; one **Let's Encrypt DNS-01 wildcard** `*.challs.ingeniums.club` (issued via CF API DNS records on the free plan using a zone-scoped DNS:Edit token — ZeroSSL no-card fallback also works) slides into `certs/fullchain.pem` + `privkey.pem`, and Traefik is restarted after every renewal because `watch:false` means Traefik won't hot-reload. All traffic on 443 (instancer `https`) and 1337 (pwn tcp-ssl via SNI `HostSNI`) is gray-cloud direct to the OpenScaler gateway's assigned ports; CF proxying those hostnames is deliberately avoided because the 3-label depth (`<prefix>-<uid>.challs.…`) is beyond Universal SSL's 1-level limit and upgrading to ACM/Total TLS would violate the zero-dollar/no-card constraint. Nothing paid anywhere: LE/ZeroSSL (free), CF DNS records (free), API token (free), Tunnels (free), OpenScaler = existing VMs.

For an alternative fully-CF-routed (orange-everywhere) topology in future, the lever would be setting `INSTANCES_HOST` to a hostname that is itself one label under a dedicated CF zone (so instance hostnames stay one label deep and are Universal-SSL-covered); tunnel routes could then handle both `https`-suffixed and plain `http` endpoints without any origin cert. Otherwise the only path to covering deeper hostnames at the CF edge is Advanced Certificate Manager / Total TLS — out of scope under the no-card constraint.
