# Rumor Mill

Linux CTF challenge — Rumor series, #1. Easy, 100–300 points.
Flag format: `ingehack{...}`.

A static SSH container. Four non-root accounts, chained handover notes, one
decoy. Players start as `y4ss1n3` and `su` through `n0d4` to `boul3h14`.

## Local build and run

```sh
docker build -t rumor-mill:local .
docker run -d --name rumor-mill \
  --hostname challenge-rumor-mill \
  -p 2222:2222 \
  -e 'FLAG=ingehack{su_1s_n0t_4lm1ghty_y0u_kn0w}' \
  rumor-mill:local
```

CI injects the flag from `chall.yaml` (`ops/deploy-static.sh` passes it as
`FLAG`), so the image itself never bakes it. The entrypoint stages the value
root-only and re-execs with a clean environment, keeping it out of
`/proc/1/environ`.

## Verify

```sh
docker exec rumor-mill /verify.sh
CONTAINER=rumor-mill solution/verify_solution.sh
```

`verify.sh` runs every check from the challenge spec as root inside the
container, dropping to `y4ss1n3` for the player-facing checks, and exits 0
only when all pass.

## Player connection (deployed)

```sh
ssh -o ProxyCommand='openssl s_client -quiet -servername %h -connect %h:%p' \
    y4ss1n3@rumor-mill.challs.ingeniums.club -p 9464
# password: Welcome123
```

The mapped `tcp-ssl` port comes from `docs/status.md` (`1337 → 9464`).
`tcpPort: 2222` is the container port Traefik forwards to.

## Notes and deviations

1. **Decoy delivery uses the spec's ACL fallback.** A named-user ACL on
   `/home/gh3nj4/flag.txt` forces the file to `0640` and its directory to
   `0710`, breaking the mandatory `0700`/`0600` hardening. The fallback
   `/home/boul3h14/gh3nj4_flag_copy.txt` (`boul3h14:boul3h14`, `0600`) holds
   the same decoy.
2. **`pam_faillock` is provided by `libpam-modules`** on Ubuntu 22.04; there is
   no separate package.
3. **`gh3nj4`'s password is generated at container start**, not image build, so
   it never lands in an image layer. It lives only in
   `/root/gh3nj4_password.txt` (mode 600).
4. **Hostname:** the image supports `--hostname challenge-rumor-mill`. Docker
   does not grant `CAP_SYS_ADMIN`, so the entrypoint cannot set it at runtime;
   `ops/deploy-static.sh` does not pass `--hostname`, so in the CI deployment
   the hostname is the container id unless that ops script adds the flag.
5. **`pam_motd` is disabled** in `/etc/pam.d/sshd`; it writes a `0644`
   `~/.cache/motd.legal-displayed` into a player's home on every login, which
   would break the `0600` invariant. `PrintMotd yes` still shows `/etc/motd`.
