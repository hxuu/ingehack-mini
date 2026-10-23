# ADR 0005: Merged challenge PR ⇒ live challenge via CI

Date: 2026-10-23. Status: accepted.

## Context

Ingehack Mini's promise to challenge authors is that they never host anything
and never touch the platform: an author clones this repo, authors a challenge
with `new-challenge`, and opens a PR. On merge the challenge is live for
players. We are on GitHub and want that promise enforced by CI/CD, not by a
manual maintainer step.

Constraints: zero-dollar (ADR 0002); secrets never in the repo (ADR 0004);
challenge containers run on the Challs VM via the rCTF v2 Docker instancer,
pulling images at instance start.

## Decision

1. GitHub Actions workflow (`.github/workflows/challenges.yml`), triggered when
   a change under `challenges/:category:/:name:/` merges to main:
   - **Build + push**: `docker build` the challenge; push image to public
     GHCR (`ghcr.io/<org>/<challenge-name>`). Public image = zero-cost pull
     from the Challs instancer at instance start.
   - **Register**: call the platform's rCTF v2 admin API over
     `https://ctf.ingeniums.club` (the Cloudflare tunnel origin) with a
     challenge editor admin token held as a GitHub Actions secret. The
     resulting challenge config makes the instancer pull the GHCR image.
2. The registering bot is a dedicated admin promoted with only
   `challsRead|challsWrite` (perms = 3), NOT the maintainer's full admin. A
   leaked Actions secret cannot touch settings, users, leaderboard export, or
   delete solves.
3. Merged challenges are visible immediately; rCTF's start-time gate still
   controls when players can see/solve them, so no extra "publish" gate in CI.

## Consequences

- Authors: merge = live. The only ship artifact is the PR itself.
- One integration test is owed: confirm the Challs instancer can pull from
  public GHCR on instance start (not verified yet — do it during
  hello-instancer E2E work).
- Admin token rotation is a GitHub-secret edit, not full admin rotation.
