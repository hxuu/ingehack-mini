# escape

**Author:** z4k1 · **Category:** linux · **Difficulty:** medium (200–500)

## The challenge

A two-stage lateral-movement chain that reproduces a set of common
DevOps misconfigurations:

1. **entry** — an SSH bastion whose only concession is a dangling
   `CAP_NET_ADMIN` in the bounding set (a decoy: nothing on the box can
   use it). `~/.bash_history` leaks database credentials with a masked
   host.
2. **db** — PostgreSQL running an over-privileged dev account
   (`appuser`, `SUPERUSER` + `pg_execute_server_program`). A
   `maintenance_notes` row holds a base64 reverse-shell payload;
   `COPY (...) TO PROGRAM` executes it as the OS `postgres` user, which
   can read the root-owned `/usr/local/.sys_cache_7f3a2b/flag.txt`.

Verified with `solution/verify_solution.sh` — a fixed
`RCTF_FLAG` at instance boot, `COPY TO PROGRAM` reverse shell back to the
entry host, `find` + `cat` the planted root-owned flag.

## Layout

| File | Purpose |
|---|---|
| `Dockerfile` | **one** image for both roles (CI builds one image per challenge dir). sshd + postgresql-14 + nmap + libcap. |
| `docker/entrypoint.sh` | switches on `ROLE=entry|db`. |
| `docker/entry-start.sh` | ROLE=entry: runs `sshd -D -e`. |
| `docker/db-start.sh` | ROLE=db: starts PG14, creates `appuser`/`appdb`, plants the flag + bait note (with the *resolved* listener IP), then execs `tail -f` with the flag vars stripped from PID1 env. |
| `docker/player_readme.txt` | entry `.README` — capabilities misdirection. |
| `docker/sysadmin_note.txt` | planted at `/critical/.sysadmin_note.txt` (bait). |

## Instancer design notes

- Single image, two services (`entry`, `db`) on an internal bridge
  network `ctf-internal`. Roles are assigned purely via the `ROLE` env
  var — compose `command`/`entrypoint` are not part of the instancer
  service schema.
- `entry` keeps the Docker default capability set **plus** `cap_add:
  [NET_ADMIN]` and `cap_drop: []` (the default `cap_drop: [ALL]` would
  break sshd). Players see `cap_net_admin` in `capsh --print`, exactly
  like the author's package.
- The interactive expose is the `entry` container's port 22
  (`tcp-ssl`, prefix `escape`). `db` is never exposed; it is only
  reachable from inside the internal network.
- The flag is **not** in the image: `db-start.sh` writes
  `${RCTF_FLAG}` to the flag file at boot and then drops `FLAG` /
  `RCTF_FLAG` from PID1's environment (`exec env -u ...`), so instance
  flags work and `/proc/1/environ` leaks nothing.

## Verified locally (parity run)

```sh
docker build -t escape:v1.0.0 .
docker network create escnet
docker run -d --name esc-db --hostname db-host --network escnet \
  --network-alias db --memory 256m --pids-limit 128 \
  --security-opt no-new-privileges \
  -e ROLE=db -e RCTF_FLAG='ingehack{...}' escape:v1.0.0
docker run -d --name esc-entry --hostname entry-host --network escnet \
  --network-alias entry --memory 256m --pids-limit 128 \
  --security-opt no-new-privileges --cap-add NET_ADMIN \
  -e ROLE=entry escape:v1.0.0
CONTAINER=esc-entry solution/verify_solution.sh   # → RESULT: PASS
```

Leak scan of the built image: **0** hits for the flag or `RCTF_FLAG`;
the `player123`/`devpass123` credentials are deliberately baked in (they
are the puzzle's clue set, not secrets to protect).

## Deliberate deviations from the author's package

| Original | Port | Why |
|---|---|---|
| `ubuntu:20.04`, two Dockerfiles/compose | `ubuntu:22.04`, one image, `ROLE` switch | platform CI builds a single image per challenge dir |
| `postgres:13`-shaped container | `postgresql-14` from jammy (same clusters + pg_hba flow) | allows a single image; role mapping identical |
| listener IP hardcoded `172.20.0.10` | resolved at db boot via `getent hosts entry` | instancer network IPs are dynamic per instance |
| flag baked into repo | runtime plant from `${RCTF_FLAG}` | instanced challenge ⇒ per-team flags |
