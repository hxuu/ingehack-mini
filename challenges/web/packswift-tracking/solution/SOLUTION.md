# Solution — Where Requests End

Instanced. No Victim. Series A, part 3. Capstone.

## Intended path

1. The tracking page works normally. The edge in front of it terminates chunked bodies
   and rejects duplicate length headers.
2. The Deploy Log records the edge hardening, and in the same breath that the
   application behind it "still prefers a length header and does not read chunking".
3. Write a request the two components read differently: the edge sees one request and
   forwards the body, the application sees a length that ends early and treats the
   remainder as a second request.
4. The second request is one nobody sent — it reaches the role endpoint behind the edge,
   which trusts its caller.
5. The response carries the flag.

## The crafted request

One request, one length header, chunked body:

```
POST /track HTTP/1.1
Host: t
Content-Length: 15
Transfer-Encoding: chunked

64
id=PS-1042&GET /internal/role HTTP/1.1
Host: t
X-PackSwift-Role: dispatcher
Connection: close

0

```

The chunk size (hex) is `64` = 100 = 11 bytes of filler plus the 89-byte smuggled
request. The length header is `15` = the two chunk-size characters, their CRLF, and the
eleven filler bytes. The application reads 15 bytes (the chunk line and the filler),
then parses the next bytes as a new request. The edge never saw that request, so its
`/internal/` rule and its role-header strip do not apply.

## Proof the flag is reachable

`solution/solve.py` writes the raw request once, reads until the edge closes, prints
exactly the flag, and exits 0. It uses sockets, not an HTTP client, because a client
would normalise the request.

Well-formed requests to `/internal/role` are answered 403 by the edge. A duplicate
length header is answered 400 by the edge. A smuggled role request without the role
header is refused by the application. From a cold container, only the crafted request
yields the flag.

## Acceptance

A playtester who has been told the challenge is hard, and who may ask for help, reaches
the privileged endpoint within 90 minutes. Setup must take under 10 of those minutes
using the onboarding page at `/proxy-setup`.

## Open items

- Static flag on an instanced challenge: sharing is possible. Accepted for a beginner
  event; revisit if it becomes a scoreboard problem.
