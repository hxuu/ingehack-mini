# Platform ingress via Cloudflare Tunnel; Challenge VM grey-clouded with a Let's Encrypt wildcard

Public IPs on OpenScaler are shared per-region and change when VMs are
recreated — DNS records pointing at the IP would rot immediately, and
Cloudflare only proxies a fixed port whitelist that OpenScaler's auto-assigned
mapped ports never fall into. So the Platform is served via a Cloudflare
Tunnel (token-managed, `ctf.ingeniums.club` orange → `localhost:9479`), which
eliminates both problems and takes the Platform off the shared gateway
entirely.

The Challenge VM is deliberately grey-clouded (no Cloudflare proxy on
`*.challs.ingeniums.club`):

1. `tcp-ssl` (pwn) endpoints need raw TLS/SNI passthrough, impossible for
   arbitrary tools behind Cloudflare's HTTP-level proxy.
2. Orange-clouding the two-label hostnames
   `hello-<uid>.challs.ingeniums.club` would require Advanced Certificate
   Manager — a paid add-on requiring card verification, violating the event's
   zero-dollar constraint.

Instead, one Let's Encrypt wildcard `*.challs.ingeniums.club` (+ apex) is
obtained via certbot DNS-01 with a zone-scoped Zone:DNS:Edit API token (free,
no payment info disclosed), handed to Traefik on the Challenge VM, and
terminated there for both 443 (web) and 1337 (tcp-ssl) traffic. Renewal runs
through a deploy hook (`/etc/letsencrypt/renewal-hooks/deploy/restart-traefik.sh`)
that copies certs and restarts Traefik — Traefik's file provider has
`watch: false` upstream, so a reload is required by design.

## Status

accepted (2026-10-22/23)

## Considered options

- Cloudflare Tunnel for `*.challs` too (would avoid mapped ports for web
  challenges): rejected — the two-label wildcard needs the paid ACM edge cert.
- Caddy/nginx TLS in front of the Challenge VM's Traefik: rejected — the
  instancer's Traefik already terminates TLS per-instance; a second terminator
  buys nothing.

## Consequences

- Platform `rctf.d/02-ctf.yaml` sets `origin: https://ctf.ingeniums.club`,
  `proxy.cloudflare: true`, `proxy.trust: 1` (cloudflared → bundled nginx =
  one hop; more hops would let clients spoof `X-Forwarded-For` and dodge
  per-IP rate limits).
- DNS: `*.challs` CNAME → `app.alpha.openscaler.net` (the gateway hostname,
  stable across VM churn). Never point a record at the IP itself.
- No edge WAF/rate limiting on challenge traffic (grey cloud); the
  per-challenge resource limits in `instancerConfig` are the only containment.
- Web challenge URLs carry an explicit mapped port
  (`https://<instance-hostname>:9471`) because the gateway routes by port,
  not hostname — a cosmetic wart until OpenScaler grants dedicated public
  IPs, at which point everything flips to standard ports and plain A records.
