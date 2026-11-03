# Rumor Mill #3 — The Liars' Club

Hard Linux CTF challenge (Rumor series, #3 of 3, finale). **500 points.**
Flag format: `ingehack{...}`.

A static SSH container (`tcpPort: 2222`) on Ubuntu 22.04. Every note lies;
the auth log is the only truth.

## Layout

```text
challenges/linux/rumor-mill-3/
├── chall.yaml          # static flag, tcp-ssl description, points 500/500
├── Dockerfile
├── src/
│   ├── entrypoint.sh   # users, files, encrypted flag, log, hardening
│   └── sshd_config
├── solution/
│   ├── solve.md
│   └── verify_solution.sh
├── verify.sh           # 82-check suite (run as root)
└── README.md
```

## Local build and run

```sh
docker build -t rumor-mill-3:mini .

docker run -d --name rumor-mill-3-liars-mini \
  --hostname challenge-rumor-mill-3 \
  -p 2227:2222 \
  -e 'FLAG=ingehack{3v3ry0n3_l13d_bu7_th3_l0g_d1dn7}' \
  rumor-mill-3:mini
```

Host port **2227** keeps this clear of Rumor #1 (2222/2223) and #2
(2224/2225); the standalone build uses **2226**.

The entrypoint stages `FLAG` root-only and re-execs with `env -i`, so it never
appears in `/proc/1/environ`. The image contains no plaintext flag, key, or
fixed password.

## Verify

```sh
docker exec rumor-mill-3-liars-mini /verify.sh
CONTAINER=rumor-mill-3-liars-mini solution/verify_solution.sh
```

## Player connection (deployed)

```sh
ssh -o ProxyCommand='openssl s_client -quiet -servername %h -connect %h:%p' \
    y4ss1n3@rumor-mill-3.challs.ingeniums.club -p 9450
# password: 4rt4z4
```

The mapped `tcp-ssl` port comes from `docs/status.md` (`1337 → 9450`).
`tcpPort: 2222` is the container port Traefik forwards to.

## Intended path

`y4ss1n3` → `n0d4` → `boul3h14` → flag:

1. `onboarding.txt` decodes to `matdiresh` — stale, rejected by `su`.
2. `nohup.out` leaks the real n0d4 password.
3. `README` lies about separator/order; `/var/log/rumor/auth.log` shows
   `printf "%s_%s" "9atchal" "lweld"`.
4. `flag.txt` → `.confession` → `gh3nj4/.cache/.flag_backup` is a decoy and
   is unreadable (`0711` homes, `0600` files).
5. `.recovery.txt`'s old key produces garbage; `audit_copy.log` points at
   `n0d4/.sync`.
6. The real log names `boul3h14/.sync`; `.notes.txt` holds the base64 key;
   `.backup.bin` decrypts to the real flag.

Full commands: `solution/solve.md`.

## Notes / deviations

1. **`points` is `{min: 500, max: 500}`** because `ops/chall-payload.py`
   requires the map form. The effective value is exactly the spec's 500.
2. **`--cap-drop=ALL` cannot run this challenge.** With all capabilities
   dropped, `useradd`/`chpasswd` fail and `sshd` cannot spawn user sessions
   (`useradd: failure while writing changes to /etc/shadow`,
   `Connection refused`).
3. **`--security-opt=no-new-privileges` cannot run this challenge.** It stops
   the setuid `su` binary from gaining root, which is the only transition in
   the intended path (`su: Authentication failure` with a correct password).
   Docker's default capability set is used; the player account still has no
   effective capabilities, no sudo, no SUID helper, and no file capabilities.
4. **H17/H18 are platform-limited.** `/proc/sys` is read-only in an
   unprivileged container and Docker's `--sysctl` rejects `kernel.*` keys.
   `verify.sh` reports the observed host values and marks the item
   `platform-limited`.
5. **H25 (`chattr +i`)** reports `Operation not supported` on overlayfs; the
   verifier accepts the documented exception.
6. **`/home/boul3h14/.sync` is `0711 root:root`** so `ls` by `boul3h14` fails
   (MF25) while known-path reads still work.
