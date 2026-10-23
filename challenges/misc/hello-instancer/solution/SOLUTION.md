# solution — hello-instancer

1. On the platform challenge page press Start; the instancer gives a host
   `hello-http-<uid>.challs.ingeniums.club:<public-port>` (three expose
   variants: http :port80, https :port443, tcp-ssl :port1337 — the ports map
   via published mapped ports recorded in docs/status.md).
2. Load `/flag` on that host (through any of the three kinds).
3. The flag is the team-baked dynamic flag, e.g.
   `ingehack{7h15_Ba5e_...leet...}` — unique per team.
4. Submit on the platform.

Verify isolation: two teams' `/flag` responses differ.

```sh
curl -s "http://<your-instance-host>:<public-port>/flag"
```
