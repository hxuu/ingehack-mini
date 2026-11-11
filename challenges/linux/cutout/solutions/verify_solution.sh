#!/usr/bin/env bash
# verify_solution.sh — automated player-side solve for Cutout.
# Runs AS uid boul3h14 inside the container (docker exec -u boul3h14 …);
# exits 0 only when the full chain reconstructs the real flag.
exec python3 - <<'PYEOF'
import os, sys, time, subprocess

EXPECTED = "ingehack{ch41n_0f_cust0dy}"
LEDGER = "/var/lib/vendor-tool/.ledger"


def step(n, msg):
    print(f"[{n}] {msg}", flush=True)


def die(n, msg):
    print(f"FAIL[{n}]: {msg}", file=sys.stderr)
    sys.exit(1)


# 1 — recon: world-visible /opt split key + ledger
step(1, "read /opt/vendor-tool split key + /var ledger")
# leftover triggers from an earlier session would poison the classification
for lab in os.listdir("/tmp"):
    if lab.endswith(".trigger"):
        try:
            os.unlink(os.path.join("/tmp", lab))
        except OSError:
            pass
k1 = open("/opt/vendor-tool/lib/.part1").readline().strip()
k2 = open("/opt/vendor-tool/share/.part2").readline().strip()
assert (k1, k2) == ("v3rm1l10n", "0bs1d14n"), (k1, k2)
rows = [l.strip().split() for l in open(LEDGER) if l.strip() and not l.startswith("#")]
assert len(rows) == 6, rows
key_rows = [r for r in rows if r[2] == "key"]
assert len(key_rows) == 1 and key_rows[0][1] == "2048", key_rows

labels = [r[0] for r in rows]
step(1, f"6 ledger labels: {labels}")


def trigger(label, code):
    with open(f"/tmp/{label}.trigger", "w") as fh:
        fh.write(code)


def holder_for(label, timeout=6.0):
    """Holder pids are static — the keeper publishes its pid at boot."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(f"/run/cutout/{label}.holder") as fh:
                return int(fh.read().strip())
        except OSError:
            time.sleep(0.1)
    return None


def fd_content(pid, timeout=9.0):
    """Poll /proc/<pid>/fd/3 until the daemon's 10 s window is open.
    Empty read = keeper's /dev/null placeholder (no fd handed over yet)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            d = open(f"/proc/{pid}/fd/3", "rb").read()
            if d:
                return d
        except OSError:
            pass
        time.sleep(0.1)
    return None


def blob2payload(blob, offset, length, key):
    return bytes(b ^ key[i % len(key)]
                 for i, b in enumerate(blob[offset:offset + length]))


# 2 — find P1: 'start' is published in /tmp/p1.unlock
step(2, "trigger all labels with 'start'; exactly one opens")
p1_label = None
for lab in labels:
    trigger(lab, "start")
time.sleep(1.2)
for lab in labels:
    hp = holder_for(lab, 3.0)
    c = fd_content(hp, 3.0) if hp else None
    if c == b"ingehack{":
        p1_label = lab
        break
assert p1_label, "no label accepted 'start'"
step(2, f"P1 = {p1_label} → fd3 discloses the next unlock code: ingehack{{")

# 3 — middle chain: every label except P1 takes 'ingehack{'. P2/P3 reply with
# 14-byte decoys, P4/P6 hold their 4096-byte blob, and P5 rejects 'ingehack{'
# so its daemon never opens a window (keeper fd stays the empty placeholder).
step(3, "trigger remaining labels with 'ingehack{'; classify responses")
opened, blobs = {}, {}
rest = [lab for lab in labels if lab != p1_label]
key_label = next(r[0] for r in rows if r[2] == "key")
# settle: any fd a keeper still holds from an earlier session (e.g. a verify
# run seconds ago) must expire first — wait until every non-P1 holder's fd/3
# reads empty (the /dev/null placeholder) before triggering.
def settled(lab, hp, deadline=16.0):
    end = time.time() + deadline
    while time.time() < end:
        try:
            d = open(f"/proc/{hp}/fd/3", "rb").read()
            if not d:
                return True          # placeholder only (empty /dev/null)
        except FileNotFoundError:
            return True              # fd closed = idle (keeper's post-hold state)
        except OSError:
            pass
        time.sleep(0.25)
    return False

step(3, "waiting for all held fds to expire (≤12 s keeper holds)")
for lab in rest:
    trigger(lab, "pip")          # bogus code: wakes daemons but matches none
time.sleep(2.0)                  # let daemons consume/clear their trigger files
for lab in rest:
    hp = holder_for(lab, 6.0)
    if hp:
        assert settled(lab, hp), f"keeper for {lab} still holding a stale fd"
step(3, "all keepers idle (held fds expired)")
for lab in rest:
    trigger(lab, "ingehack{")
time.sleep(1.2)
p5_candidates = []
for lab in rest:
    hp = holder_for(lab, 8.0)
    c = fd_content(hp) if hp else None
    if c is None:
        p5_candidates.append(lab)
    elif len(c) == 14:
        opened[lab] = ("decoy", c)
    elif len(c) == 4096:
        blobs[lab] = c
assert len(p5_candidates) == 1, p5_candidates
p5_label = p5_candidates[0]
assert key_label in blobs, "P6 (ledger key row) produced no blob"
assert len(opened) == 2, opened
assert set(c for _, c in opened.values()) == {b"ingehack{f4k3_"}, opened
assert len(blobs) == 2, blobs
step(3, "2 decoys replied 'ingehack{f4k3_'; 2 blobs (P4, P6) captured")

# 4 — P5 accepts only P4's plaintext 'ch41n_'
step(4, f"{p5_label} accepts only 'ch41n_' (P4's plaintext)")
trigger(p5_label, "ch41n_")
time.sleep(1.2)
hp = holder_for(p5_label, 8.0)
assert hp, "no holder for P5"
p5blob = fd_content(hp)
assert p5blob and len(p5blob) == 4096, "P5 blob malformed"
blobs[p5_label] = p5blob

# 5 — P6 (ledger: purpose key, offset 2048) decrypts with the /opt combined key
step(5, "decrypt P6 with v3rm1l10n+0bs1d14n @2048 → real key")
combined = (k1 + k2).encode()
key_label = key_rows[0][0]      # same row the ledger gave in step 3
assert key_label in blobs, "P6 blob missing"
real_key = blob2payload(blobs[key_label], 2048, 17, combined)
assert real_key == b"r34l_k3y_0bs1d14n", real_key
step(5, f"real key = {real_key.decode()}")

# 6 — P4 (plaintext ch41n_) and P5 (0f_cust0dy}) decrypt @1024 under the real key
step(6, "decrypt P4/P5 with the real key @1024")
p4_label = next(l for l in labels if l in blobs and l != key_label and l != p5_label)
p4c = blob2payload(blobs[p4_label], 1024, 6, real_key)
p5c = blob2payload(blobs[p5_label], 1024, 11, real_key)
assert p4c == b"ch41n_", p4c
assert p5c == b"0f_cust0dy}", p5c
step(6, "fragments recovered: ch41n_ | 0f_cust0dy}")

# 7 — assemble, then cleanup
flag = (b"ingehack{" + p4c + p5c).decode()
step(7, f"flag = {flag}")
if flag != EXPECTED:
    die(7, f"assembled {flag!r} != {EXPECTED!r}")
for lab in labels:
    try:
        os.unlink(f"/tmp/{lab}.trigger")
    except OSError:
        pass
print(f"FLAG: {flag}")
print("RESULT: PASS")
sys.exit(0)
PYEOF
