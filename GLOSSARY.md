# Inge MiniCTF Infrastructure

The domain language for running the ingeniums.club miniCTF: a 48-hour jeopardy
Ctf for first-year students, hosted on rCTF v2 across two OpenScaler VMs behind
Cloudflare. This glossary is for infra maintainers; challenge-author or
player-facing language lives with the event content, not here.

## Language

### Platforms and where things run

**Platform**:
The rCTF v2 application (web + API + Postgres + Redis) that players log into.
The Platform alone never runs challenge containers.
_Avoid_: Main box, server, rCTF host

**Challenge VM (Challs)**:
The separate VM where challenge containers are created and run. Deliberately
the more resource-rich machine (8 vCPU / 16 GB) because instances stack here.
_Avoid_: Instancer VM, worker

**Staging**:
An (optional, currently absent) disposable VM mirroring Challs for pre-event
testing that cannot risk the live instancer.
_Avoid_: Dev VM

**Gateway**:
OpenScaler's shared public IP entry point for all VMs in the region. Traffic
reaches a VM only through a **Mapped Port**; the provider cannot route by
hostname. When a VM is deleted its public IP is lost, but the gateway hostname
stays stable — records therefore point at the gateway, never the IP.
_Avoid_: Load balancer, edge

**Mapped Port**:
An auto-assigned public gateway port forwarding to an internal VM port
(e.g. `443 → 9471`). Public ports are re-assigned on VM recreation, so never
hard-code them in player-facing material without re-checking.
_Avoid_: Port forward, NAT rule

### Challenges and instances

**Challenge**:
A task registered in the Platform with flags, category, and concept tags. May
exist as a *static* challenge (no runtime) or an *instanced* challenge (see
below). One record per challenge, stable `challengeIntegrationId`.
_Avoid_: Problem, task, chall

**Challenge Instance**:
A per-team ephemeral copy of an instanced Challenge's container(s), started on
the Challenge VM through the instancer, with a per-team flag baked in at
launch. Belongs to exactly one Team; expires after a timeout and can be
extended.
_Avoid_: Docker instance, container (a container is what backs an instance,
not the abstraction players see)

**Instancer**:
The service that creates, routes, extends, and expires Challenge Instances.
Here: rCTF's Docker instancer (Traefik + Redis + tiny-instancer) on the
Challenge VM, addressed by the Platform over the private network.
_Avoid_: Docker daemon, orchestrator

**Expose**:
A declared player-facing endpoint of a Challenge Instance, with a `kind`
(`http` / `https` / `tcp-ssl`) and a `hostPrefix`. `tcp` is silently rewritten
to `tcp-ssl`; pwn challenges are always `tcp-ssl`.
_Avoid_: Port mapping (reserved for Mapped Port), endpoint URL

**Instance Hostname**:
The per-instance DNS name the instancer generates:
`<hostPrefix>-<uid>.<INSTANCES_HOST>`. One label under `INSTANCES_HOST`, so a
single-level wildcard cert covers every instance.
_Avoid_: Instance URL (that includes port and kind)

### Networking and ingress

**Tunnel (Platform path)**:
The Cloudflare Tunnel carrying orange-clouded `ctf.ingeniums.club` to the
Platform. The only ingress for the Platform; the Gateway port is fallback
only.
_Avoid_: Zero Trust (Cloudflare product name for the dashboard this lives in —
confusing in a CTF context)

**Grey Cloud (Challs path)**:
The deliberate decision NOT to proxy `*.challs` through Cloudflare: challenge
traffic is direct TLS via Mapped Ports. Required for `tcp-ssl`; also frees us
from a paid edge certificate.
_Avoid_: Direct path, bypass

**Instances Host (`INSTANCES_HOST`)**:
The domain under which instance hostnames are published
(`challs.ingeniums.club`). Changing it invalidates existing instance
hostnames; requires a Traefik wildcard cert to match.
_Avoid_: Instance domain

### Event rules

**Division**:
rCTF's user class (here only `open`). Exists as an extension point; not used
to separate skill levels this year.
_Avoid_: Category (categories are the challenge taxonomy: Web/Crypto/Forensics/Misc)

**Concept Tag**:
The free-form tag on a Challenge (e.g. `HTTP Protocol`, `Browser Trust
Boundaries`) that marks which first-year CS concept the challenge teaches —
the pedagogical layer on top of the jeopardy Category.
_Avoid_: Label, keyword

**Sanity Challenge**:
A guided onboarding challenge walking beginners through DevTools/HTTP/terminal
basics; part of the MISC taxonomy with beginners as the primary audience.
_Avoid_: Tutorial, warmup (acceptable in player-facing prose but not in records)
**Write-up**:
A player-submitted solution description, locked per-challenge until the
player solves it, flat-bonus scored, published post-event. Not yet wired into
the platform.
_Avoid_: Solution, report

**Score Decay**:
rCTF dynamic points: a Challenge's point value falls as solve count rises,
between a configured max and min. (Default provider: `scores/classic`.)
_Avoid_: Dynamic scoring (fine in prose; the mechanism is decay)
