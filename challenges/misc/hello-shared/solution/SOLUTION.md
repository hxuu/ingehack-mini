# solution — hello-shared (static, shared instance)

Walkthrough, so review can verify the intended path:

1. Open the URL from the description: `http://hello-shared.challs.ingeniums.club:9487/`.
   The counter increments on every reload — it is shared between all teams.
2. The page says the flag is on another path of the same host, but not in the
   body: request `GET /flag`.
3. In dev tools (F12 → Network), click the request → Response headers →
   `X-Flag: ingehack{same_server_every_team}` (fixed; shared).
   (`curl -si` shows the same header from a terminal — note lowercase `-si`,
   a HEAD probe with `-sI` gets a 501.)
4. Submit it on the platform.

Solver one-liner:

```sh
curl -si "http://hello-shared.challs.ingeniums.club:9487/flag" | grep -i x-flag
```
