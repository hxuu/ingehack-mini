# ADR 0006: The Skin ships as a rebuilt rCTF image, pinned by the Platform's own version variable

Date: 2026-11-01. Status: accepted.

## Context

Ingehack Mini runs the stock rCTF v2 image
(`ghcr.io/otter-sec/rctf:${RCTF_GIT_REF}`, `RCTF_GIT_REF=main`) on the Platform
VM. We wanted the event to carry its own look, and rCTF v2 offers no way to do
that at runtime: theming is source-level (colours in
`apps/web/src/styles/color.css`, categories in
`apps/web/src/lib/utils/categories.ts`), and there is no config key for custom
CSS/JS or an uploadable theme directory the way CTFd has one. A Skin here can
only be a source overlay on the web app, so it lives in a private fork of
rCTF, `hxuu/ingehack-skin`.

Constraints: zero-dollar (ADR 0002), secrets only on the VMs or in Actions
secrets (ADR 0004), and no staging VM, so a Skin Release goes straight onto the
live Platform and has to be reversible quickly.

## Decision

1. A **Skin** is a branch of the fork; a **Skin Release** is a tag on it,
   deployed as a **Skin Image**. Releases are built locally (or by the fork's
   CI), shipped by `docker save | ssh minictf-platform docker load`, and the
   Platform is pointed at one by setting `RCTF_GIT_REF` in `/opt/rctf/.env`,
   followed by `docker compose up -d --force-recreate rctf`. No registry is
   involved, the same registry-less shipping the challenge pipeline uses
   (ADR 0005).
2. A Skin Release is based on **the upstream commit the Platform is already
   running**, not on the newest upstream `main`. Rebasing the skin onto the
   live base keeps a release's delta purely presentational, which is what makes
   "only the look changed" checkable after the fact.
3. The upstream `:main` image stays on the VM. Rolling back is setting
   `RCTF_GIT_REF=main` and recreating — one env value, seconds of downtime.
4. Flipping `RCTF_GIT_REF` is a human action. CI builds and loads Skin Images;
   it never moves the Platform's front door.

## Consequences

- A Skin Release is tied to an upstream rCTF version and must be rebased when
  upstream moves; the fork carries the whole platform, not just a theme.
- The image tag keeps the upstream repository name (`ghcr.io/otter-sec/rctf:…`)
  because `/opt/rctf/compose.yml` composes it from `RCTF_GIT_REF`. The tag is a
  local name for a locally loaded image; nothing is pulled from that registry.
- Skin-only changes still deploy as whole images, so the platform restarts
  briefly on each release. Acceptable while the event is unpublished; revisit if
  releases ever need to be seamless.
