# Solution — Course Finder

Static container. The library assistant runs on the platform's admin-bot worker
(`admin-bot.ts` in this directory, attached through `adminBot:` in `chall.yaml`).

## Intended path

1. Search for anything. The query is reflected into the results page unencoded.
2. Try a script tag. It does not run: the response carries `script-src 'self'`.
3. The footer links the source, which shows a legacy `/api/jsonp` endpoint still used
   by the old course widget.
4. Point a script tag at that endpoint with the payload in its callback parameter — it
   is same-origin, so the policy permits it.
5. Submit the crafted `/search?q=...` URL through the run-bot form on the challenge
   page. The worker signs the assistant in with her password — which is the team's
   flag, attached to the job at run time and never present in the (public) handler
   source — and then opens the link. The payload runs in her session and posts her
   private note into the player's own inbox, so no external listener is needed.
6. Reload the student inbox and read the note.

## Proof the flag is reachable

The player's inbox contains the note after the assistant's visit. The note is never
returned to an unauthenticated request, and `/api/me/note` only answers an
`assistant` session: her password is the flag, minted at the platform, so nobody
signs in as her directly. The student pass on the login page is re-minted every boot
and every credential lives outside `/src`.

## Verified (2026-11-06, local containers)

`solution/solve.py --stage prepare` builds the target URL, a browser signed in as the
assistant opened it, and `--stage submit` read the flag out of the student inbox. The
full two-stage run is the `challenge-review` load: prepare → run the bot (platform
admin-bot, or locally `victim/visit.py` with `FLAG` in the environment) → submit.

## Acceptance

A playtester working from source gets a script to execute against the assistant within
25 minutes, and understands that the policy allowed the gadget rather than being absent.
