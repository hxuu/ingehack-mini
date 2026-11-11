#!/usr/bin/env bash
# gen_setup.sh — Cutout build-time generator (runs INSIDE the image build).
# Labels are regenerated each build; contents come from the spec's constants.
# Source of truth at build output: /root/cutout_labels.json (0600).
set -euo pipefail

# ---------------------------------------------------------------- users ----
getent passwd boul3h14 >/dev/null || /usr/sbin/useradd -m -u 1001 -s /bin/bash -c '' boul3h14
getent passwd ch41n    >/dev/null || /usr/sbin/useradd -m -u 1002 -s /bin/bash -c '' ch41n
getent passwd gh0st    >/dev/null || /usr/sbin/useradd -m -u 1003 -s /usr/sbin/nologin -c '' gh0st

printf 'boul3h14:Welcome123\n' | chpasswd
P_CH41N="$(head -c 24 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)"
P_GH0ST="$(head -c 24 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)"
printf 'ch41n:%s\n' "$P_CH41N" | chpasswd
printf 'gh0st:%s\n' "$P_GH0ST" | chpasswd
printf '%s\n' "$P_CH41N" > /root/ch41n_password.txt
printf '%s\n' "$P_GH0ST" > /root/gh0st_password.txt
chmod 600 /root/ch41n_password.txt /root/gh0st_password.txt

# ------------------------------------------------------------ labels -------
python3 - <<'PY'
import os, json
labels = {}
while len(labels) < 6:
    lab = os.urandom(4).hex()
    if lab not in labels.values():
        labels[f"P{len(labels)+1}"] = lab
with open("/root/cutout_labels.json", "w") as fh:
    json.dump(labels, fh, indent=2)
os.chmod("/root/cutout_labels.json", 0o600)
print("labels:", json.dumps(labels))
PY

# ------------------------------------------------------- homes / ledger ----
python3 - <<'PY'
import os, json, pwd, shutil

labels = json.load(open("/root/cutout_labels.json"))

H = "/home/ch41n"
shutil.rmtree(f"{H}/fragments", ignore_errors=True)
shutil.rmtree(f"{H}/unlocks", ignore_errors=True)
for sub in ("fragments", "unlocks"):
    p = f"{H}/{sub}"
    os.makedirs(p)
    os.chmod(p, 0o700)

FRAG = {
    "P1": b"ingehack{",
    "P2": b"ingehack{f4k3_",
    "P3": b"ingehack{f4k3_",
    "P4": b"ch41n_",
    "P5": b"0f_cust0dy}",
    "P6": b"r34l_k3y_0bs1d14n",
}
UNLOCK = {
    "P1": "start",
    "P2": "ingehack{",
    "P3": "ingehack{",
    "P4": "ingehack{",
    "P5": "ch41n_",
    "P6": "ingehack{",
}
for role in ("P1","P2","P3","P4","P5","P6"):
    lab = labels[role]
    with open(f"{H}/fragments/{lab}", "wb") as fh:
        fh.write(FRAG[role])
    with open(f"{H}/unlocks/{lab}", "w") as fh:
        fh.write(UNLOCK[role])

rows = [f"{labels[r]} 1024 fragment" for r in ("P1","P2","P3","P4","P5")]
rows.append(f"{labels['P6']} 2048 key")
os.makedirs("/var/lib/vendor-tool", exist_ok=True)
with open("/var/lib/vendor-tool/.ledger", "w") as fh:
    fh.write("# Vendor Tool Ledger\n# Format: <process-label> <offset> <purpose>\n")
    fh.write("\n".join(rows) + "\n")
os.chmod("/var/lib/vendor-tool/.ledger", 0o644)

with open("/tmp/p1.unlock", "w") as fh:
    fh.write("start")
os.chmod("/tmp/p1.unlock", 0o644)

with open("/home/gh0st/flag.txt", "wb") as fh:
    fh.write(b"ingehack{th1s_1s_4_f4k3_fl4g}")

with open("/home/boul3h14/.bash_history", "w") as fh:
    fh.write("ls\nwhoami\n")

for owner_name in ("ch41n", "gh0st", "boul3h14"):
    pw = pwd.getpwnam(owner_name)
    shutil.chown(f"/home/{owner_name}", pw.pw_uid, pw.pw_gid)
    os.chmod(f"/home/{owner_name}", 0o700)
    # every file in the home is owned by the user, mode 600 (dirs 700) —
    # includes the /etc/skel dotfiles, which land root-owned 644 by default
    for root, dirs, fs in os.walk(f"/home/{owner_name}"):
        for d in dirs:
            dp = os.path.join(root, d)
            shutil.chown(dp, pw.pw_uid, pw.pw_gid)
            os.chmod(dp, 0o700)
        for f in fs:
            fp = os.path.join(root, f)
            shutil.chown(fp, pw.pw_uid, pw.pw_gid)
            os.chmod(fp, 0o600)

cw = pwd.getpwnam("ch41n")
for role in ("P1","P2","P3","P4","P5","P6"):
    for sub in ("fragments", "unlocks"):
        p = f"{H}/{sub}/{labels[role]}"
        shutil.chown(p, cw.pw_uid, cw.pw_gid)
        os.chmod(p, 0o600)
shutil.chown(f"{H}/fragments", cw.pw_uid, cw.pw_gid)
shutil.chown(f"{H}/unlocks",   cw.pw_uid, cw.pw_gid)
shutil.chown(f"{H}/ch41n.py", cw.pw_uid, cw.pw_gid)

sg = pwd.getpwnam("gh0st")
shutil.chown("/home/gh0st/flag.txt", sg.pw_uid, sg.pw_gid)
os.chmod("/home/gh0st/flag.txt", 0o600)

sb = pwd.getpwnam("boul3h14")
shutil.chown("/home/boul3h14/.bash_history", sb.pw_uid, sb.pw_gid)
os.chmod("/home/boul3h14/.bash_history", 0o600)
print("homes staged")
PY

# -------------------------------------------------------------- units ------
python3 - <<'PY'
import json
labels = json.load(open("/root/cutout_labels.json"))
for role, lab in labels.items():
    path = f"/etc/systemd/system/cutout-P{role[1:]}.service"
    txt = open(path).read()
    txt = txt.replace("/usr/local/bin/cutout-run P%s" % role[1:],
                      "/usr/bin/python3 /home/ch41n/ch41n.py %s" % lab)
    open(path, "w").write(txt)
print("units resolved with random labels")
PY

systemctl daemon-reload 2>/dev/null || true
systemctl enable cutout-P1 cutout-P2 cutout-P3 cutout-P4 cutout-P5 cutout-P6 2>/dev/null || \
    { mkdir -p /etc/systemd/system/multi-user.target.wants; \
      for i in 1 2 3 4 5 6; do \
        ln -sf ../cutout-P$i.service /etc/systemd/system/multi-user.target.wants/cutout-P$i.service; \
      done; }
systemctl enable cutout-sshd cutout-keeper 2>/dev/null || \
    { mkdir -p /etc/systemd/system/multi-user.target.wants; \
      ln -sf ../cutout-sshd.service    /etc/systemd/system/multi-user.target.wants/cutout-sshd.service; \
      ln -sf ../cutout-keeper.service  /etc/systemd/system/multi-user.target.wants/cutout-keeper.service; }
systemctl enable cutout-watchdog.timer 2>/dev/null || \
    { mkdir -p /etc/systemd/system/timers.target.wants; \
      ln -sf ../cutout-watchdog.timer /etc/systemd/system/timers.target.wants/cutout-watchdog.timer; }

# --------------------------------------------------------- hardening -------
# 2. no sudo membership / no sudoers entries
for grp in sudo wheel; do
    getent group "$grp" >/dev/null 2>&1 || true
    gpasswd -d ch41n "$grp" 2>/dev/null || true
    gpasswd -d boul3h14 "$grp" 2>/dev/null || true
done

# 3. pam_faillock active on /etc/pam.d/su (preauth AND authfail)
PAM_SEC="$(ls -d /usr/lib/*-linux-gnu/security 2>/dev/null | head -1)"
if [ -d "$PAM_SEC" ] && [ -f "$PAM_SEC/pam_faillock.so" ]; then
    grep -q pam_faillock /etc/pam.d/su || cat >> /etc/pam.d/su <<'EOF'
# Cutout: faillock (preauth + authfail)
auth required pam_faillock.so preauth deny=5 unlock_time=900
auth required pam_faillock.so authfail deny=5 unlock_time=900
EOF
else
    echo "WARN: pam_faillock.so not present" >&2
fi

# 5. no cron/at jobs
systemctl disable cron.timer cron.service atd.service 2>/dev/null || true
rm -rf /etc/cron.d /etc/cron.daily /etc/cron.weekly /etc/cron.monthly 2>/dev/null || true

# 8. GECOS empty
python3 - <<'PY'
fields = ("boul3h14", "ch41n", "gh0st")
lines = open("/etc/passwd").read().splitlines()
out = []
for line in lines:
    f = line.split(":")
    if f[0] in fields:
        f[4] = ""
        line = ":".join(f)
    out.append(line)
open("/etc/passwd", "w").write("\n".join(out) + "\n")
PY

# 9. /etc/shadow 640 root:shadow
chmod 640 /etc/shadow
chown root:shadow /etc/shadow 2>/dev/null || true

# 10. sshd
mkdir -p /var/run/sshd
ssh-keygen -A >/dev/null
cat > /etc/ssh/sshd_config <<'EOF'
Port 22
Protocol 2
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication no
AllowUsers boul3h14
X11Forwarding no
PrintMotd yes
UsePAM yes
PidFile /run/sshd.pid
EOF
chmod 600 /etc/ssh/sshd_config

# 11+D3. kernel knobs are host-side; pin them in config files (deviation D3)
cat > /etc/sysctl.d/99-cutout-hardening.conf <<'EOF'
# Cutout deployment baseline (host-side knobs — see handoff deviation D3)
kernel.yama.ptrace_scope = 3
kernel.core_pattern = /dev/null
EOF
cat > /etc/security/limits.d/99-cutout.conf <<'EOF'
* hard core 0
* soft core 0
EOF

# 13. banners
printf 'Authorized access only.\n' > /etc/issue
printf 'Authorized access only.\n' > /etc/motd

# 14. timezone + hostname
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
echo "Etc/UTC" > /etc/timezone
printf 'challenge-cutout\n' > /etc/hostname

apt-get clean
rm -rf /var/lib/apt/lists/*
echo "gen_setup: done"
