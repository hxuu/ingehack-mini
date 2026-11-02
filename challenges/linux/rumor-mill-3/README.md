# Rumor Mill #3 — Dead Drop

Hard Linux CTF challenge — Rumor series, #3. **Hard, 400–800 points.**
Flag format: `ingehack{...}`.

A static SSH container (`tcpPort: 2222`) on Ubuntu 22.04. Four non-root
accounts, a mailbox with a lying third party, a dotfiles repo whose history was
rewritten, a symmetric-encrypted dead drop, and a root archive helper that
trusts its own working directory.

## Layout

```text
challenges/linux/rumor-mill-3/
├── chall.yaml          # static flag, tcp-ssl description, 400–800 pts
├── Dockerfile
├── src/
│   ├── entrypoint.sh   # users, mail, drop, repo, sudo helper, hardening
│   └── sshd_config     # port 2222, AllowUsers, no root login
├── solution/
│   ├── solve.md
│   └── verify_solution.sh
├── verify.sh           # 90-check suite (run as root)
└── README.md
```

## Local build and run

```sh
docker build -t rumor-mill-3:local .

docker run -d --name rumor-mill-3 \
  --hostname challenge-rumor-mill-3 \
  -p 2227:2222 \
  -e 'FLAG=ingehack{d34d_dr0ps_sp34k_l0ud3r_th4n_w0rds}' \
  rumor-mill-3:local
```

Host port **2227** maps to container port **2222** so this never clashes with
Rumor Mill #1 (2222/2223) or #2 (2224/2225).

CI injects the flag from `chall.yaml` (`ops/deploy-static.sh` passes it as
`FLAG`), so the image itself never bakes it. The entrypoint stages the value
root-only and re-execs with a clean environment, keeping it out of
`/proc/1/environ`.

## Verify

```sh
docker exec rumor-mill-3 /verify.sh
CONTAINER=rumor-mill-3 solution/verify_solution.sh
```

`verify.sh` re-execs with `FLAG` removed so the environment scan cannot be
masked by `docker exec` inheriting the container config. It covers the
must-fail/must-succeed player path, the git and gpg hops, the tar wildcard
privesc (it is actually executed), hardening H1–H30, and explicit flag-leak
checks.

## Player connection (deployed)

```sh
ssh -o ProxyCommand='openssl s_client -quiet -servername %h -connect %h:%p' \
    y4ss1n3@rumor-mill-3.challs.ingeniums.club -p 9464
# password: Welcome123
```

The mapped `tcp-ssl` port comes from `docs/status.md` (`1337 → 9464`).
`tcpPort: 2222` is the container port Traefik forwards to.

## Intended path

`y4ss1n3` → `n0d4` → `boul3h14` → root:

1. `/var/mail/y4ss1n3` holds two password halves and one lie from `gh3nj4`.
2. `n0d4`'s dotfiles repo keeps the drop passphrase in a **dangling commit**
   after a history rewrite (`git fsck --lost-found`, `git show`).
3. `gpg --batch --pinentry-mode loopback --passphrase ... --decrypt
   dead-drop.gpg` yields `boul3h14`'s password.
4. `sudo -l` exposes one helper; `tar czf ... *` in a player-writable
   directory is vulnerable to **GNU tar wildcard injection**
   (`--checkpoint-action=exec`), giving root.
5. `/root/dead-drop/flag.txt` (`0600`) holds the flag; `gh3nj4` holds a decoy.

## Notes and deviations

1. **One sudo rule, and it is the privesc.** Ubuntu's `sudo` is installed
   because the challenge needs it; the verifier asserts the rule is the only
   root command available to `boul3h14` and that no file capabilities or
   non-stock SUID binaries provide another path.
2. **`--pinentry-mode loopback` is required.** `pinentry-curses` cannot drive a
   dialog over this sshd, so `note.txt` gives the exact `gpg` invocation. Keep
   that note in sync if the encryption command ever changes.
3. **`tar` version matters.** `--checkpoint-action=exec` exists since tar 1.30;
   Ubuntu 22.04 ships 1.34, and the verifier executes the exploit so a base
   image bump cannot silently break it.
4. **`/home` is `0711`, each home is `0700`**, every file under `/home` is
   `0600`, matching the series convention.
