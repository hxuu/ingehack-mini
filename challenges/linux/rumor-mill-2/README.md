# Rumor Mill #2 — The Encoded Rumor

Linux CTF challenge — Rumor series, #2. Medium, 200–500 points.
Flag format: `ingehack{...}`.

A static SSH container (`tcpPort: 2222`) on Ubuntu 22.04. Four non-root
accounts, a stale handover note, a rotated password, base64-encoded password
fragments with a decoy, and an AES-256-CBC encrypted flag.

## Layout

```text
challenges/linux/rumor-mill-2/
├── chall.yaml          # static flag, tcp-ssl description, 200–500 pts
├── Dockerfile
├── src/
│   ├── entrypoint.sh   # users, files, hardening, sshd (root, runtime)
│   └── sshd_config     # port 2222, AllowUsers, no root login
├── solution/
│   ├── solve.md
│   └── verify_solution.sh
├── verify.sh           # 78-check suite (run as root)
└── README.md
```

## Local build and run

```sh
docker build -t rumor-mill-2:local .

docker run -d --name rumor-mill-2 \
  --hostname challenge-rumor-mill-2 \
  -p 2225:2222 \
  -e 'FLAG=ingehack{rum0rs_4r3_b4s364_4ll_th3_w4y_d0wn}' \
  rumor-mill-2:local
```

CI injects the flag from `chall.yaml` (`ops/deploy-static.sh` passes it as
`FLAG`), so the image itself never bakes it. The entrypoint stages the value
root-only and re-execs with a clean environment, keeping it out of
`/proc/1/environ`. The plaintext flag is not present in `entrypoint.sh`,
`verify.sh`, or any copied solution directory.

## Verify

```sh
docker exec rumor-mill-2 /verify.sh
CONTAINER=rumor-mill-2 solution/verify_solution.sh
```

`verify.sh` re-execs with `FLAG` removed so the environment scan cannot be
masked by `docker exec` inheriting the container config. It covers the
must-fail/must-succeed player path, hardening H1–H25, and explicit flag-leak
checks (`/entrypoint.sh`, `/verify.sh`, `/solutions`, `/etc/rumor-mill/flag`,
readable homes).

## Player connection (local)

Host port **2225** maps to container port **2222** so this challenge never
clashes with Rumor Mill #1 (2222) or its ingehack-mini build (2223):

```sh
ssh -p 2225 y4ss1n3@localhost
# password: Welcome123
```

## Player connection (deployed)

```sh
ssh -o ProxyCommand='openssl s_client -quiet -servername %h -connect %h:%p' \
    y4ss1n3@rumor-mill-2.challs.ingeniums.club -p 9450
# password: Welcome123
```

The mapped `tcp-ssl` port comes from `docs/status.md` (`1337 → 9450`).
`tcpPort: 2222` is the container port Traefik forwards to.

## Intended path

`y4ss1n3` → `n0d4` → `boul3h14`:

1. `onboarding.txt` has a stale base64 password; `.bash_history` points at
   `.env`, which has the rotated one (`K4r4k0_1962_v2`).
2. `n0d4`'s `.part_order` decodes to `2,3,1`; the parts decode to
   `h4y`, `3l1y4`, `ws4y`; `.part4` is a decoy (`n0p3`).
3. `boul3h14`'s password is `h4y_3l1y4_ws4y`.
4. `.key.b64` decodes to `matdiresh_el_3rab`; decrypt `flag.txt` with
   `openssl enc -d -aes-256-cbc -a -pbkdf2`.

`gh3nj4` holds only the decoy flag.

## Notes and deviations

1. **No plaintext flag in the image scripts.** The original repo baked the
   flag into `/entrypoint.sh`, `/verify.sh`, and `/solutions/*`, all
   world-readable. This version injects the flag via `FLAG`, keeps a root-only
   `0600` copy at `/etc/rumor-mill/flag`, and does not copy `solution/` into the
   image.
2. **`pam_faillock` is provided by `libpam-modules`** on Ubuntu 22.04; there is
   no separate package. It is configured on `su`, `sshd`, and `login`.
3. **`gh3nj4`'s password is generated at container start**, not image build, so
   it never lands in an image layer. It lives only in
   `/root/gh3nj4_password.txt` (mode 600).
4. **`pam_motd` is intentionally omitted** from `/etc/pam.d/sshd`; it writes a
   `0644` `~/.cache/motd.legal-displayed` into a player's home on every login,
   which would break the `0600` invariant. The pre-auth `Banner` shows
   `Authorized access only.` and `/etc/motd` holds the same line.
5. **Hostname:** the image supports `--hostname challenge-rumor-mill-2`.
   Docker does not grant `CAP_SYS_ADMIN`, so the entrypoint cannot set it at
   runtime; the local run command sets it.
6. **`/home` is `0711`, each home is `0700`.** That is the #2 spec's own
   convention: `/home` is traversable but not listable, and each home is
   private.
