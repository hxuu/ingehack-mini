# solution — hello (static)

Walkthrough, so review can verify the intended path:

1. Open the challenge; the endpoint is plain HTTP: `http://<mapped-port host>/`.
2. The page says the flag is served on a different path of the same host.
3. Request `GET /flag` (address bar: append `/flag`).
4. Response body is `ingehack{http_is_just_requests}` (fixed; shared).
5. Submit it on the platform.

Solver one-liner:

```sh
curl -s "http://<hello-host>:<public-port>/flag"
```
