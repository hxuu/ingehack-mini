# ADR 0007: The fork also carries platform patches, released on their own line

Date: 2026-11-01. Status: accepted.

## Context

ADR 0006 gave the event its look by forking rCTF (`hxuu/ingehack-skin`) and
shipping Skin Images. That decision also framed a Skin Release as *purely
presentational* — it ships the whole platform, but its delta is only how it
looks, which is what makes "only the look changed" checkable.

The first thing we wanted that the stock platform could not do was not
presentational. Authors hold `challsRead` (permission `1`) so they can read
challenges, but every participant endpoint hard-filters `hidden` and
`releaseTime` for everyone: the list came back empty, and the detail endpoints
answered `badChallenge`. An author had no way to check their own work the way a
participant will see it. No config key exposes hidden challenges to a
participant view — rCTF has no "preview as participant" mode — so the only fix
is a source change in the API.

We have exactly one image vehicle (ADR 0006), no registry, and no staging VM.

## Decision

1. The fork also carries **Platform Patches**: small, deliberate **behavioural**
   changes to the API/web that the event needs and upstream does not offer.
   They are not Skins and do not pretend to be.
2. A Platform Patch ships as a **Platform Image** on the same fork, on its own
   tag (`ingehack-author-preview-vN`, and a new name per patch line), built and
   shipped the same way as a Skin Image: `docker save | ssh minictf-platform
   docker load`, then `RCTF_GIT_REF` in `/opt/rctf/.env` plus
   `docker compose up -d --force-recreate rctf`. Rollback is unchanged.
3. A Platform Image is based on the live release, so it carries the Skin plus
   the patch. The patch is listed in `docs/status.md` and, where it changes
   participant-visible behaviour, stated plainly in the release notes.
4. Platform Patches stay minimal and each is small enough to re-derive by hand
   from upstream if the fork is ever dropped. Prefer a fix that reads like the
   upstream code already meant it (here: the participant routes already declare
   `onlyWhenStartedPermissionsBypass: challsRead`; the services simply never
   consulted the caller).

## First patch: `challsRead` previews hidden challenges

`includeHidden` is plumbed through the participant challenge services
(`getChallenges`, `getChallengeScoresWithPosition`, `submitFlag`,
`getChallengeSolvesResponse`) and set from the authenticated user's
`challsRead` bit on the participant list, solves, scores, submit, and instance
routes. With no token, or without `challsRead`, the `hidden`/`releaseTime`
filter still applies exactly as before; the integration tests assert both
directions.

## Consequences

- The fork is no longer only a theme; its README states which patches it
  carries beyond the visual layer.
- "Only the look changed" is no longer true for every image. Each Platform
  Image must say what it changes beyond the look, and the live-behaviour check
  a Skin Release gets (anonymous responses byte-identical across the swap) does
  not apply to it — the patch's own tests are the evidence.
- Upstreaming remains the exit: if otter-sec accepts the preview behaviour, the
  patch line retires and the Skin returns to being the fork's only delta.
